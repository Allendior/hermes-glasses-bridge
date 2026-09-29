from __future__ import annotations

import hmac
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
from pathlib import Path
import threading
from urllib.parse import parse_qs, urlparse

from .config import Settings, normalize_language
from .hermes import HermesClient, HermesError
from .speech import SpeechError, SpeechService


LOGGER = logging.getLogger(__name__)


def public_upstream_error(error: Exception) -> str:
    """Return a stable client message without leaking provider or local details."""
    LOGGER.warning("upstream request failed: %s", type(error).__name__)
    return "upstream service unavailable"


def validated_text(value: object, max_chars: int) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError("text is required")
    if len(text) > max_chars:
        raise ValueError(f"text is too long (maximum {max_chars} characters)")
    return text


class BridgeApplication:
    def __init__(self, settings: Settings, audio_dir: Path):
        self.settings = settings
        self.hermes = HermesClient(settings.hermes_base_url, settings.hermes_api_key)
        self.speech = SpeechService(settings, audio_dir)
        self._work_slots = threading.BoundedSemaphore(settings.max_concurrent_requests)

    def try_acquire_work(self) -> bool:
        return self._work_slots.acquire(blocking=False)

    def release_work(self) -> None:
        self._work_slots.release()


class BridgeHandler(BaseHTTPRequestHandler):
    server_version = "HermesVoiceBridge/0.1"

    @property
    def app(self) -> BridgeApplication:
        return self.server.app  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.client_address[0]} - {format % args}")

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        expected = f"Bearer {self.app.settings.bridge_api_key}"
        actual = self.headers.get("Authorization", "")
        return hmac.compare_digest(actual, expected)

    def _require_auth(self) -> bool:
        if self._authorized():
            return True
        self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
        return False

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 1_000_000:
            raise ValueError("invalid request size")
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object")
        return payload

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            self._json(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "hermes": "reachable" if self.app.hermes.health() else "unreachable",
                    "tts_provider": self.app.settings.tts_provider,
                    "languages": ["en", "hi", "fr"],
                },
            )
            return
        if path.startswith("/v1/audio/"):
            if not self._require_auth():
                return
            audio_id = path.rsplit("/", 1)[-1]
            if not audio_id.isalnum():
                self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid audio id"})
                return
            matches = list(self.app.speech.audio_dir.glob(f"{audio_id}.*"))
            if len(matches) != 1:
                self._json(HTTPStatus.NOT_FOUND, {"error": "audio not found"})
                return
            audio_path = matches[0]
            body = audio_path.read_bytes()
            media_type = "audio/wav" if audio_path.suffix == ".wav" else "audio/aiff"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", media_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "private, max-age=3600")
            self.end_headers()
            self.wfile.write(body)
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:
        if not self._require_auth():
            return
        if not self.app.try_acquire_work():
            self._json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {"error": "bridge is busy, try again shortly"},
            )
            return
        try:
            self._handle_post()
        finally:
            self.app.release_work()

    def _handle_post(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/v1/turn":
                payload = self._read_json()
                text = validated_text(
                    payload.get("text"), self.app.settings.max_text_chars
                )
                language = normalize_language(payload.get("language"))
                session_value = payload.get("session_id")
                session_id = str(session_value).strip() if session_value else None
                reply, session_id = self.app.hermes.turn(text, session_id, language)
                response = {
                    "session_id": session_id,
                    "language": language,
                    "text": reply,
                    "audio_url": None,
                }
                if payload.get("speak", True):
                    audio_id, _, _ = self.app.speech.synthesize(reply, language)
                    response["audio_url"] = f"/v1/audio/{audio_id}"
                self._json(HTTPStatus.OK, response)
                return
            if parsed.path == "/v1/synthesize":
                payload = self._read_json()
                text = validated_text(
                    payload.get("text"), self.app.settings.max_text_chars
                )
                language = normalize_language(payload.get("language"))
                audio_id, _, media_type = self.app.speech.synthesize(text, language)
                self._json(
                    HTTPStatus.CREATED,
                    {
                        "language": language,
                        "media_type": media_type,
                        "audio_url": f"/v1/audio/{audio_id}",
                    },
                )
                return
            if parsed.path == "/v1/transcribe":
                language = normalize_language(
                    parse_qs(parsed.query).get("language", ["en"])[0]
                )
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 25_000_000:
                    raise ValueError("audio body must be between 1 byte and 25 MB")
                audio = self.rfile.read(length)
                transcript = self.app.speech.transcribe(
                    audio,
                    language,
                    self.headers.get("Content-Type", "application/octet-stream"),
                )
                self._json(
                    HTTPStatus.OK,
                    {"language": language, "text": transcript},
                )
                return
            self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
        except json.JSONDecodeError:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid JSON"})
        except ValueError as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except (HermesError, SpeechError) as exc:
            self._json(
                HTTPStatus.BAD_GATEWAY,
                {"error": public_upstream_error(exc)},
            )


def make_server(settings: Settings, audio_dir: Path) -> ThreadingHTTPServer:
    settings.validate()
    server = ThreadingHTTPServer((settings.bridge_host, settings.bridge_port), BridgeHandler)
    server.app = BridgeApplication(settings, audio_dir)  # type: ignore[attr-defined]
    return server


def main() -> None:
    settings = Settings.from_env()
    audio_dir = Path(__file__).resolve().parent.parent / "work" / "audio"
    server = make_server(settings, audio_dir)
    print(f"Hermes voice bridge listening on http://{settings.bridge_host}:{settings.bridge_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

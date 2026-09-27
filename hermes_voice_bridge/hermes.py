from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid


LANGUAGE_INSTRUCTIONS = {
    "en": "Answer in natural English.",
    "hi": "Answer in natural Hindi, using Devanagari script unless the user asks otherwise.",
    "fr": "Answer in natural French.",
}


class HermesError(RuntimeError):
    pass


class HermesClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 300.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise HermesError(f"Hermes returned HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise HermesError(f"Could not reach Hermes: {exc}") from exc

    def health(self) -> bool:
        try:
            payload = self._request("GET", "/health")
            return payload.get("status") in {"ok", "healthy"}
        except HermesError:
            return False

    def create_session(self) -> str:
        session_id = f"glasses_{uuid.uuid4().hex}"
        payload = self._request(
            "POST",
            "/api/sessions",
            {
                "id": session_id,
                "source": "api_server",
            },
        )
        return str(payload.get("session", {}).get("id") or session_id)

    def turn(
        self, text: str, session_id: str | None = None, language: str = "en"
    ) -> tuple[str, str]:
        current_session = session_id or self.create_session()
        try:
            language_instruction = LANGUAGE_INSTRUCTIONS[language]
        except KeyError as exc:
            raise ValueError(f"unsupported Hermes response language: {language}") from exc
        payload = self._request(
            "POST",
            f"/api/sessions/{current_session}/chat",
            {
                "message": text,
                "instructions": (
                    "You are answering a spoken question for a hands-free glasses client. "
                    f"{language_instruction} "
                    "HARD LIMIT: answer in at most two sentences and under 240 characters. "
                    "Every character is spoken aloud by a slow voice synthesiser, so length is "
                    "latency the wearer physically waits through. Lead with the single most "
                    "useful fact and stop. Omit preamble, restating the question, caveats, "
                    "pleasantries and sign-offs. Give one number or one recommendation rather "
                    "than a list of options. If the honest answer truly cannot fit, give the "
                    "headline only and add 'ask me for details'. "
                    "Never use Markdown, tables, bullet points or emoji: they are unreadable "
                    "aloud."
                ),
            },
        )
        response_text = payload.get("message", {}).get("content")
        if not isinstance(response_text, str) or not response_text.strip():
            raise HermesError("Hermes returned an empty response")
        return response_text, str(payload.get("session_id") or current_session)

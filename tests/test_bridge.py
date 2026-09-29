from __future__ import annotations

from pathlib import Path
import os
import tempfile
import time
import unittest

from hermes_voice_bridge.config import Settings, normalize_language
from hermes_voice_bridge.hermes import HermesClient, HermesError, limit_spoken_reply
from hermes_voice_bridge.server import (
    BridgeApplication,
    public_upstream_error,
    validated_text,
)
from hermes_voice_bridge.speech import SpeechError, SpeechService


ROOT = Path(__file__).resolve().parent.parent


def settings(**changes):
    values = dict(
        bridge_host="127.0.0.1",
        bridge_port=8787,
        bridge_api_key="b" * 32,
        hermes_base_url="http://127.0.0.1:1",
        hermes_api_key="h" * 32,
        tts_provider="macos",
        tts_command="",
        tts_reference_audio="",
        stt_command="",
        audio_ttl_seconds=3600,
        max_concurrent_requests=2,
        max_text_chars=2_000,
        voices={"en": "Samantha", "hi": "Lekha", "fr": "Thomas"},
    )
    values.update(changes)
    return Settings(**values)


class ConfigTests(unittest.TestCase):
    def test_language_normalization(self):
        self.assertEqual(normalize_language("fr-CA"), "fr")
        with self.assertRaises(ValueError):
            normalize_language("de")


class HermesClientTests(unittest.TestCase):
    def setUp(self):
        self.client = HermesClient("http://hermes.test", "test-key")
        self.requests = []

        def fake_request(method, path, body=None):
            self.requests.append((method, path, body))
            if path == "/api/sessions":
                return {"session": {"id": body["id"]}}
            session_id = path.split("/")[3]
            return {
                "session_id": session_id,
                "message": {"role": "assistant", "content": "A sourced answer."},
            }

        self.client._request = fake_request

    def test_persistent_turn(self):
        reply, session_id = self.client.turn("What happened?", language="en")
        self.assertEqual(reply, "A sourced answer.")
        self.assertTrue(session_id.startswith("glasses_"))
        second_reply, second_session = self.client.turn(
            "Tell me more", session_id, language="fr"
        )
        self.assertEqual(second_reply, "A sourced answer.")
        self.assertEqual(second_session, session_id)
        self.assertEqual(len(self.requests), 3)
        self.assertIn("natural English", self.requests[1][2]["instructions"])
        self.assertIn("natural French", self.requests[2][2]["instructions"])

    def test_spoken_reply_is_enforced_server_side(self):
        reply = limit_spoken_reply("word " * 80)
        self.assertLessEqual(len(reply), 240)
        self.assertTrue(reply.endswith("..."))


class PublicReleaseTests(unittest.TestCase):
    def test_text_input_is_bounded(self):
        self.assertEqual(validated_text(" hello ", 10), "hello")
        with self.assertRaisesRegex(ValueError, "required"):
            validated_text("   ", 10)
        with self.assertRaisesRegex(ValueError, "too long"):
            validated_text("123456", 5)

    def test_expensive_work_has_a_bounded_concurrency_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            app = BridgeApplication(
                settings(max_concurrent_requests=1), Path(temp) / "audio"
            )
            self.assertTrue(app.try_acquire_work())
            self.assertFalse(app.try_acquire_work())
            app.release_work()
            self.assertTrue(app.try_acquire_work())
            app.release_work()

    def test_upstream_errors_are_not_exposed_to_clients(self):
        for error in (
            HermesError("provider said secret internal detail"),
            SpeechError("command stderr with a private path"),
        ):
            with self.subTest(error=type(error).__name__):
                with self.assertLogs("hermes_voice_bridge.server", level="WARNING"):
                    message = public_upstream_error(error)
                self.assertEqual(message, "upstream service unavailable")

    def test_e2e_script_uses_runtime_bridge_key(self):
        script = (ROOT / "scripts" / "e2e_target_test.sh").read_text(encoding="utf-8")
        self.assertNotIn("Bearer ***", script)
        self.assertIn('auth_header="Authorization: Bearer ${BRIDGE_API_KEY}"', script)
        self.assertIn(' -H "$auth_header" ', script)

    def test_voice_model_revision_is_pinned(self):
        script = (ROOT / "scripts" / "chatterbox_tts.py").read_text(encoding="utf-8")
        self.assertIn("DEFAULT_MODEL_REVISION", script)
        self.assertIn("revision=args.model_revision", script)

    def test_installer_has_preview_and_uninstall_paths(self):
        installer = (ROOT / "scripts" / "install_service.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("--dry-run", installer)
        self.assertTrue((ROOT / "scripts" / "remove_service.sh").is_file())

    def test_configure_script_does_not_read_hermes_private_env(self):
        script = (ROOT / "scripts" / "configure_target.py").read_text(encoding="utf-8")
        self.assertNotIn('Path.home() / ".hermes" / ".env"', script)
        self.assertIn('os.environ.get("API_SERVER_KEY")', script)


class SettingsTests(unittest.TestCase):
    def test_wildcard_bind_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "wildcard"):
            settings(bridge_host="0.0.0.0").validate()

    def test_only_loopback_or_tailscale_bind_is_allowed(self):
        settings(bridge_host="127.0.0.1").validate()
        settings(bridge_host="100.64.0.1").validate()
        settings(bridge_host="100.127.255.254").validate()
        for host in ("192.168.1.10", "10.0.0.8", "8.8.8.8", "bridge.local"):
            with self.subTest(host=host):
                with self.assertRaisesRegex(ValueError, "loopback or Tailscale"):
                    settings(bridge_host=host).validate()

    def test_command_provider_requires_reference_audio(self):
        with self.assertRaisesRegex(ValueError, "TTS_REFERENCE_AUDIO"):
            settings(tts_provider="command", tts_command="tts").validate()


class SpeechServiceTests(unittest.TestCase):
    def test_audio_directory_is_private(self):
        with tempfile.TemporaryDirectory() as temp:
            audio_dir = Path(temp) / "audio"
            SpeechService(settings(), audio_dir)
            self.assertEqual(audio_dir.stat().st_mode & 0o777, 0o700)

    def test_expired_audio_is_removed_at_startup(self):
        with tempfile.TemporaryDirectory() as temp:
            audio_dir = Path(temp) / "audio"
            audio_dir.mkdir()
            stale = audio_dir / "stale.wav"
            stale.write_bytes(b"old")
            old = time.time() - 7200
            os.utime(stale, (old, old))
            SpeechService(settings(audio_ttl_seconds=3600), audio_dir)
            self.assertFalse(stale.exists())

    def test_command_provider_receives_language_and_reference(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script = root / "fake_tts.py"
            script.write_text(
                "import pathlib,sys\n"
                "text=pathlib.Path(sys.argv[1]).read_text()\n"
                "pathlib.Path(sys.argv[2]).write_bytes((sys.argv[3]+':' + text).encode())\n"
            )
            reference = root / "voice.wav"
            reference.write_bytes(b"voice")
            cfg = settings(
                tts_provider="command",
                tts_reference_audio=str(reference),
                tts_command=f"python3 {script} {{text_file}} {{output_file}} {{language}} {{reference_audio}}",
            )
            service = SpeechService(cfg, root / "audio")
            _, output, media_type = service.synthesize("Bonjour", "fr")
            self.assertEqual(output.read_bytes(), b"fr:Bonjour")
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertEqual(media_type, "audio/wav")


if __name__ == "__main__":
    unittest.main()

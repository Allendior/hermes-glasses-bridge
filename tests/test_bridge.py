from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from hermes_voice_bridge.config import Settings, normalize_language
from hermes_voice_bridge.hermes import HermesClient
from hermes_voice_bridge.speech import SpeechService


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


class SettingsTests(unittest.TestCase):
    def test_wildcard_bind_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "wildcard"):
            settings(bridge_host="0.0.0.0").validate()

    def test_command_provider_requires_reference_audio(self):
        with self.assertRaisesRegex(ValueError, "TTS_REFERENCE_AUDIO"):
            settings(tts_provider="command", tts_command="tts").validate()


class SpeechServiceTests(unittest.TestCase):
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
            self.assertEqual(media_type, "audio/wav")


if __name__ == "__main__":
    unittest.main()

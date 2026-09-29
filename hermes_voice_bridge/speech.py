from __future__ import annotations

import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import uuid

from .config import Settings


class SpeechError(RuntimeError):
    pass


def _render_command(template: str, values: dict[str, str]) -> list[str]:
    args = shlex.split(template)
    rendered: list[str] = []
    for arg in args:
        for name, value in values.items():
            arg = arg.replace("{" + name + "}", value)
        rendered.append(arg)
    return rendered


class SpeechService:
    def __init__(self, settings: Settings, audio_dir: Path):
        self.settings = settings
        self.audio_dir = audio_dir
        self.audio_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.audio_dir, 0o700)
        self.cleanup()

    def cleanup(self) -> None:
        cutoff = __import__("time").time() - self.settings.audio_ttl_seconds
        for path in self.audio_dir.glob("*"):
            try:
                if path.is_file() and path.stat().st_mtime < cutoff:
                    path.unlink()
            except OSError:
                continue

    def synthesize(self, text: str, language: str) -> tuple[str, Path, str]:
        self.cleanup()
        audio_id = uuid.uuid4().hex
        if self.settings.tts_provider == "macos":
            output = self.audio_dir / f"{audio_id}.aiff"
            command = [
                "/usr/bin/say",
                "-v",
                self.settings.voices[language],
                "-o",
                str(output),
                text,
            ]
            media_type = "audio/aiff"
        else:
            output = self.audio_dir / f"{audio_id}.wav"
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", suffix=".txt", delete=False
            ) as handle:
                handle.write(text)
                text_file = handle.name
            command = _render_command(
                self.settings.tts_command,
                {
                    "text_file": text_file,
                    "output_file": str(output),
                    "language": language,
                    "reference_audio": self.settings.tts_reference_audio,
                },
            )
            media_type = "audio/wav"
        try:
            completed = subprocess.run(
                command, capture_output=True, text=True, timeout=300, check=False
            )
        finally:
            if self.settings.tts_provider == "command":
                try:
                    os.unlink(text_file)
                except OSError:
                    pass
        if completed.returncode != 0:
            raise SpeechError(completed.stderr.strip() or "TTS command failed")
        if not output.is_file() or output.stat().st_size == 0:
            raise SpeechError("TTS command did not create audio")
        os.chmod(output, 0o600)
        return audio_id, output, media_type

    def transcribe(self, audio: bytes, language: str, content_type: str) -> str:
        if not self.settings.stt_command:
            raise SpeechError("Local transcription is not configured")
        suffix = ".wav" if "wav" in content_type.lower() else ".audio"
        with tempfile.TemporaryDirectory(prefix="hermes-stt-") as temp_dir:
            input_file = Path(temp_dir) / f"input{suffix}"
            output_file = Path(temp_dir) / "transcript.txt"
            input_file.write_bytes(audio)
            command = _render_command(
                self.settings.stt_command,
                {
                    "input_file": str(input_file),
                    "output_file": str(output_file),
                    "language": language,
                },
            )
            completed = subprocess.run(
                command, capture_output=True, text=True, timeout=300, check=False
            )
            if completed.returncode != 0:
                raise SpeechError(completed.stderr.strip() or "STT command failed")
            if not output_file.is_file():
                raise SpeechError("STT command did not create a transcript")
            transcript = output_file.read_text(encoding="utf-8").strip()
            if not transcript:
                raise SpeechError("STT returned an empty transcript")
            return transcript


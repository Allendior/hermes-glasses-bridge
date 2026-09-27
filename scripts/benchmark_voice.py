#!/usr/bin/env python3
"""Run cold multilingual Chatterbox samples and save a machine-readable benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import wave


SAMPLES = {
    "en": "The glasses bridge is ready. This is an English voice-cloning test.",
    "hi": "चश्मे का ब्रिज तैयार है। यह हिंदी आवाज़ की जाँच है।",
    "fr": "La passerelle des lunettes est prête. Ceci est un test vocal en français.",
    "mixed": "The bridge is ready, चश्मे तैयार हैं, et le test est terminé.",
}


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as audio:
        return audio.getnframes() / audio.getframerate()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reference_audio")
    parser.add_argument("--output-dir", default="work/benchmarks")
    parser.add_argument("--model", default="mlx-community/chatterbox-multilingual-v3")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    reference = Path(args.reference_audio).expanduser().resolve()
    if not reference.is_file():
        raise SystemExit(f"reference audio not found: {reference}")
    output_dir = (root / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    records = []

    for name, text in SAMPLES.items():
        language = "en" if name == "mixed" else name
        text_file = output_dir / f"{name}.txt"
        output_file = output_dir / f"{name}.wav"
        text_file.write_text(text, encoding="utf-8")
        command = [
            sys.executable,
            str(root / "scripts" / "chatterbox_tts.py"),
            "--text-file",
            str(text_file),
            "--output",
            str(output_file),
            "--language",
            language,
            "--reference",
            str(reference),
            "--model",
            args.model,
        ]
        started = time.monotonic()
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        elapsed = time.monotonic() - started
        record = {
            "sample": name,
            "language": language,
            "elapsed_seconds": round(elapsed, 3),
            "success": completed.returncode == 0 and output_file.is_file(),
        }
        if record["success"]:
            duration = wav_duration(output_file)
            record["audio_seconds"] = round(duration, 3)
            record["real_time_factor"] = round(elapsed / duration, 3)
        else:
            record["error"] = (completed.stderr or completed.stdout)[-1000:]
        records.append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)
        if not record["success"]:
            break

    report = {
        "model": args.model,
        "reference_audio": str(reference),
        "samples": records,
    }
    (output_dir / "benchmark.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0 if len(records) == len(SAMPLES) and all(r["success"] for r in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())

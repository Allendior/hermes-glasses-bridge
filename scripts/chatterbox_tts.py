#!/usr/bin/env python3
"""Synthesize cloned speech with MLX Chatterbox Multilingual on Apple silicon."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


SUPPORTED_LANGUAGES = frozenset({"en", "hi", "fr"})
DEFAULT_MODEL = "mlx-community/chatterbox-multilingual-v3"
DEFAULT_MODEL_REVISION = "03565773edd72e949572557597af8063bb49a18a"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--language", required=True, choices=sorted(SUPPORTED_LANGUAGES))
    parser.add_argument("--reference", required=True)
    parser.add_argument("--model", default=os.environ.get("CHATTERBOX_MODEL", DEFAULT_MODEL))
    parser.add_argument(
        "--model-revision",
        default=os.environ.get("CHATTERBOX_MODEL_REVISION", DEFAULT_MODEL_REVISION),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    text_path = Path(args.text_file).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    reference_path = Path(args.reference).expanduser().resolve()

    if not text_path.is_file():
        raise SystemExit(f"text file not found: {text_path}")
    if not reference_path.is_file():
        raise SystemExit(f"reference audio not found: {reference_path}")
    text = text_path.read_text(encoding="utf-8").strip()
    if not text:
        raise SystemExit("text file is empty")

    # Import only after argument validation so configuration failures remain fast.
    from huggingface_hub import snapshot_download
    import mlx.core as mx
    import numpy as np
    from mlx_audio.audio_io import write as audio_write
    from mlx_audio.tts.utils import load_model

    model_path = snapshot_download(
        repo_id=args.model,
        revision=args.model_revision,
    )
    model = load_model(model_path)
    chunks = []
    sample_rate = model.sample_rate
    for result in model.generate(
        text=text,
        ref_audio=str(reference_path),
        lang_code=args.language,
        exaggeration=0.1,
        cfg_weight=0.5,
        temperature=0.8,
        repetition_penalty=1.2,
        min_p=0.05,
        top_p=1.0,
        max_new_tokens=1200,
        verbose=False,
    ):
        chunks.append(result.audio)
        sample_rate = result.sample_rate

    if not chunks:
        raise SystemExit("Chatterbox returned no audio")
    audio = chunks[0] if len(chunks) == 1 else mx.concatenate(chunks, axis=0)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    audio_write(str(output_path), np.asarray(audio), sample_rate, format="wav")
    if not output_path.is_file() or output_path.stat().st_size <= 44:
        raise SystemExit("Chatterbox did not create a valid WAV file")
    print(f"created {output_path} ({sample_rate} Hz)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

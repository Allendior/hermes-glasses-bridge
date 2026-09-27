#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"

if [ -f "$project_dir/.env" ]; then
  set -a
  # This file is generated locally with mode 0600 and is never committed.
  . "$project_dir/.env"
  set +a
fi

python_bin=python3
if [ -x "$project_dir/.venv/bin/python" ]; then
  python_bin="$project_dir/.venv/bin/python"
fi

exec "$python_bin" -m hermes_voice_bridge.server

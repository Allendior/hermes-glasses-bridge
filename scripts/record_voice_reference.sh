#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
duration=${1:-45}
device=${2:-:0}
output="$project_dir/work/voice-reference/owner-reference.wav"

case "$duration" in
  *[!0-9]*|'') printf 'Duration must be a whole number of seconds.\n' >&2; exit 2 ;;
esac

mkdir -p "$(dirname -- "$output")"
printf 'Recording %s seconds from AVFoundation audio device %s. Speak naturally now.\n' "$duration" "$device"
ffmpeg -hide_banner -loglevel warning -f avfoundation -i "$device" -t "$duration" \
  -ac 1 -ar 24000 -c:a pcm_s16le -y "$output"
printf 'Saved %s\n' "$output"

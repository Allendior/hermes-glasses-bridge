#!/bin/sh
set -eu

label=ai.hermes.glasses-bridge
target_plist="$HOME/Library/LaunchAgents/$label.plist"
runtime_dir="$HOME/.local/share/hermes-glasses-bridge"

launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
if [ -f "$target_plist" ]; then
  rm -f "$target_plist"
fi

printf 'Stopped and removed LaunchAgent %s.\n' "$label"
printf 'Runtime data was left at %s so keys and voice files are not destroyed.\n' "$runtime_dir"
printf 'Delete that directory yourself only when you are sure you no longer need it.\n'

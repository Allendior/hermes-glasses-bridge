#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
runtime_dir="$HOME/.local/share/hermes-glasses-bridge"
env_file="$runtime_dir/.env"
if [ ! -f "$env_file" ]; then
  env_file="$project_dir/.env"
fi

set -a
. "$env_file"
set +a

output_dir="$project_dir/work/e2e"
mkdir -p "$output_dir"
base_url="http://$BRIDGE_HOST:$BRIDGE_PORT"

health=$(curl --fail --silent --show-error --connect-timeout 5 --max-time 15 \
  "$base_url/health")
printf 'Bridge health: %s\n' "$health"

lan_ip=$(ifconfig 2>/dev/null | awk \
  '$1 == "inet" && $2 !~ /^127\./ && $2 !~ /^100\./ { print $2; exit }')
if [ -n "$lan_ip" ]; then
  if curl --silent --connect-timeout 2 --max-time 3 "http://$lan_ip:8642/health" \
    >/dev/null 2>&1; then
    printf 'FAIL Hermes is reachable on LAN address %s\n' "$lan_ip" >&2
    exit 1
  fi
  printf 'Hermes LAN isolation: OK (%s:8642 refused)\n' "$lan_ip"
  if curl --silent --connect-timeout 2 --max-time 3 "http://$lan_ip:$BRIDGE_PORT/health" \
    >/dev/null 2>&1; then
    printf 'FAIL Bridge is reachable on LAN address %s\n' "$lan_ip" >&2
    exit 1
  fi
  printf 'Bridge LAN isolation: OK (%s:%s refused)\n' "$lan_ip" "$BRIDGE_PORT"
fi

if [ -z "${BRIDGE_API_KEY:-}" ]; then
  printf 'FAIL BRIDGE_API_KEY is missing from %s\n' "$env_file" >&2
  exit 1
fi

# Keep the key in the Authorization header only. Do not print it.
auth_header="Authorization: Bearer ${BRIDGE_API_KEY}"
set +x

first_body=$(jq -nc '{text:"What is the capital of France? Answer in one short sentence.",language:"en",speak:true}')
curl --fail-with-body --silent --show-error --max-time 300 \
  -H "$auth_header" \
  -H 'Content-Type: application/json' \
  --data "$first_body" "$base_url/v1/turn" > "$output_dir/turn-en.json"

session_id=$(jq -er '.session_id' "$output_dir/turn-en.json")
audio_url=$(jq -er '.audio_url' "$output_dir/turn-en.json")
curl --fail --silent --show-error --max-time 30 \
  -H "$auth_header" \
  "$base_url$audio_url" > "$output_dir/turn-en.audio"

second_body=$(jq -nc --arg session_id "$session_id" \
  '{text:"Now answer the same question in French.",language:"fr",speak:false,session_id:$session_id}')
curl --fail-with-body --silent --show-error --max-time 300 \
  -H "$auth_header" \
  -H 'Content-Type: application/json' \
  --data "$second_body" "$base_url/v1/turn" > "$output_dir/turn-fr.json"

jq '{session_id,language,text,audio_url}' "$output_dir/turn-en.json"
jq '{session_id,language,text,audio_url}' "$output_dir/turn-fr.json"
if [ "$(jq -r .session_id "$output_dir/turn-fr.json")" != "$session_id" ]; then
  printf 'FAIL Hermes did not preserve the session id\n' >&2
  exit 1
fi
file "$output_dir/turn-en.audio"
printf 'Persistent multilingual Hermes turn and audio retrieval: OK\n'

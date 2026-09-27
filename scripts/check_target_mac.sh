#!/bin/sh
set -u

ok=0
warn=0

check_command() {
  if command -v "$1" >/dev/null 2>&1; then
    printf 'OK   %-18s %s\n' "$1" "$(command -v "$1")"
  else
    printf 'MISS %-18s not installed\n' "$1"
    warn=$((warn + 1))
  fi
}

printf 'Hermes Glasses target check\n'
printf '===========================\n'
printf 'Machine: %s / %s\n' "$(sw_vers -productVersion 2>/dev/null || echo unknown)" "$(uname -m)"

check_command hermes
check_command tailscale
check_command openssl
check_command say

if command -v hermes >/dev/null 2>&1; then
  printf '\nHermes version\n'
  hermes --version || warn=$((warn + 1))
  printf '\nHermes gateway status\n'
  if launchctl print "gui/$(id -u)/ai.hermes.gateway" >/dev/null 2>&1; then
    gateway_pid=$(launchctl print "gui/$(id -u)/ai.hermes.gateway" 2>/dev/null |
      awk '$1 == "pid" && $2 == "=" { print $3; exit }')
    printf 'OK   launchd gateway is running (supervisor PID %s)\n' "${gateway_pid:-unknown}"
  else
    hermes gateway status 2>/dev/null || printf 'INFO Gateway is not currently running.\n'
  fi
fi

if command -v tailscale >/dev/null 2>&1; then
  printf '\nTailscale addresses\n'
  if ! tailscale ip -4 2>/dev/null; then
    tail_ip=$(ifconfig 2>/dev/null | awk '$1 == "inet" && $2 ~ /^100\./ { print $2; exit }')
    if [ -n "$tail_ip" ]; then
      printf 'OK   %s (active tunnel; macOS app CLI preferences unavailable)\n' "$tail_ip"
    else
      printf 'INFO Tailscale service is not reachable from this terminal.\n'
      warn=$((warn + 1))
    fi
  fi
fi

if command -v hermes >/dev/null 2>&1; then
  printf '\nHermes API isolation\n'
  api_host=$(hermes config get API_SERVER_HOST 2>/dev/null || true)
  if [ "$api_host" = "127.0.0.1" ] || [ "$api_host" = "::1" ] || [ "$api_host" = "localhost" ]; then
    printf 'OK   API server is loopback-only (%s)\n' "$api_host"
  else
    printf 'WARN API server bind is %s; expected 127.0.0.1\n' "${api_host:-unset}"
    warn=$((warn + 1))
  fi
fi

printf '\nBridge deployment\n'
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if [ -x "$project_dir/.venv/bin/python" ] &&
   "$project_dir/.venv/bin/python" -c \
     'from importlib.metadata import version; version("mlx-audio")' >/dev/null 2>&1; then
  printf 'OK   MLX-Audio runtime installed\n'
else
  printf 'MISS MLX-Audio runtime\n'
  warn=$((warn + 1))
fi
if launchctl print "gui/$(id -u)/ai.hermes.glasses-bridge" >/dev/null 2>&1; then
  printf 'OK   launch service installed\n'
else
  printf 'MISS launch service not installed\n'
  warn=$((warn + 1))
fi

printf '\nRequired system voices\n'
for voice in Samantha Lekha Thomas; do
  if say -v '?' 2>/dev/null | awk '{print $1}' | grep -Fx "$voice" >/dev/null; then
    printf 'OK   %s\n' "$voice"
  else
    printf 'MISS %s\n' "$voice"
    warn=$((warn + 1))
  fi
done

printf '\nResult: %s warning(s).\n' "$warn"
exit "$ok"

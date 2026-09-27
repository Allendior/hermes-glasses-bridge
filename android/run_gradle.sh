#!/bin/bash
set -euo pipefail
# Respect JAVA_HOME/ANDROID_HOME if already set in the environment; otherwise
# fall back to common macOS defaults (JDK 17 via `java_home`, then Homebrew's
# openjdk@17 keg, then the SDK under ~/Library/Android/sdk). Override either
# by exporting it before running this script.
: "${JAVA_HOME:=$(/usr/libexec/java_home -v 17 2>/dev/null || true)}"
if [ -z "$JAVA_HOME" ] && [ -d /opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home ]; then
  JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
fi
: "${ANDROID_HOME:=$HOME/Library/Android/sdk}"
export JAVA_HOME ANDROID_HOME
export PATH="$JAVA_HOME/bin:$PATH"
cd "$(dirname "$0")"
exec ./gradlew --no-daemon "$@"

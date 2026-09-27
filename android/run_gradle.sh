#!/bin/bash
set -euo pipefail
export JAVA_HOME=/opt/homebrew/Cellar/openjdk@17/17.0.20/libexec/openjdk.jdk/Contents/Home
export ANDROID_HOME=/Users/allenghanghas/Library/Android/sdk
export PATH="$JAVA_HOME/bin:$PATH"
cd "$(dirname "$0")"
exec ./gradlew --no-daemon "$@"

#!/bin/bash
# Launcher script for dedicated JARVIS Chrome Profile on Mac
PROFILE_DIR="$HOME/JarvisChromeProfile"

mkdir -p "$PROFILE_DIR"
echo "Launching dedicated JARVIS Chrome window..."
echo "Profile directory: $PROFILE_DIR"
echo "Remote debugging port: 9222"

/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$PROFILE_DIR" \
  --no-first-run \
  --no-default-browser-check &

echo "JARVIS Chrome started successfully!"

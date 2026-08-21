#!/usr/bin/env bash
# Launch (or reuse) a Chrome with CDP open, on a profile of its own.
# The user logs in by hand once; agents attach to that session.
#   PORT=9333 PROFILE=~/.superqa/qa-chrome-profile ./qa-chrome.sh [url]
set -euo pipefail

PORT="${PORT:-9333}"
PROFILE="${PROFILE:-$HOME/.superqa/qa-chrome-profile}"
URL="${1:-about:blank}"

if curl -sf "http://127.0.0.1:${PORT}/json/version" >/dev/null 2>&1; then
  echo "reusing Chrome on http://127.0.0.1:${PORT}"
  exit 0
fi

find_chrome() {
  [ -n "${CHROME:-}" ] && { echo "$CHROME"; return; }
  local c
  for c in "$HOME"/.agent-browser/browsers/chrome-*/"Google Chrome for Testing.app"/Contents/MacOS/"Google Chrome for Testing" \
           "$HOME"/.cache/puppeteer/chrome/*/chrome-*/"Google Chrome for Testing.app"/Contents/MacOS/"Google Chrome for Testing" \
           "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"; do
    [ -x "$c" ] && { echo "$c"; return; }
  done
  for c in google-chrome google-chrome-stable chromium chromium-browser; do
    command -v "$c" >/dev/null 2>&1 && { command -v "$c"; return; }
  done
  return 1
}

CHROME_BIN="$(find_chrome)" || { echo "no Chrome found; set CHROME=/path/to/chrome" >&2; exit 1; }
mkdir -p "$PROFILE"

"$CHROME_BIN" --remote-debugging-port="$PORT" --user-data-dir="$PROFILE" \
  --no-first-run --no-default-browser-check "$URL" >/dev/null 2>&1 &

for _ in $(seq 1 30); do
  curl -sf "http://127.0.0.1:${PORT}/json/version" >/dev/null 2>&1 && {
    echo "Chrome ready on http://127.0.0.1:${PORT} (profile: $PROFILE)"; exit 0; }
  sleep 0.5
done
echo "Chrome did not open CDP on ${PORT}" >&2; exit 1

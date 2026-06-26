#!/usr/bin/env bash
# trigger-ci-handoff.sh — RPi-side sync trigger for the Milhy-PC CI gateway.
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MILHY_PC_HOST="${MILHY_PC_HOST:-Milhy-PC}"
MILHY_PC_REPO="${MILHY_PC_REPO:-/home/milhy777/Develop/RPi}"
STATE_FILE="${STATE_FILE:-.git/rpi-handoff-last-sha}"
RSYNC_EXCLUDES=(
  --exclude '.venv/'
  --exclude '__pycache__/'
  --exclude '*.pyc'
  --exclude '.forensics/'
  --exclude 'conductor/ci/reports/'
  --exclude 'playback-memory.json'
  --exclude 'yt-cookies.txt'
)

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Working tree dirty; not triggering CI handoff."
  exit 0
fi

HEAD_SHA="$(git rev-parse HEAD)"
LAST_SHA=""
if [[ -f "$STATE_FILE" ]]; then
  LAST_SHA="$(cat "$STATE_FILE")"
fi

if [[ "$HEAD_SHA" == "$LAST_SHA" ]]; then
  echo "No new commit since last handoff ($HEAD_SHA)."
  exit 0
fi

echo "Syncing $HEAD_SHA to $MILHY_PC_HOST:$MILHY_PC_REPO"
rsync -a --delete "${RSYNC_EXCLUDES[@]}" "$ROOT/" "$MILHY_PC_HOST:$MILHY_PC_REPO/"

printf '%s\n' "$HEAD_SHA" > "$STATE_FILE"
echo "Handoff queued for $HEAD_SHA"

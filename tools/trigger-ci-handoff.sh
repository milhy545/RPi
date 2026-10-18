#!/usr/bin/env bash
# trigger-ci-handoff.sh — RPi-side sync trigger for the Milhy-PC CI gateway.
set -Eeuo pipefail

ROOT="${ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

MILHY_PC_HOST="${MILHY_PC_HOST:-Milhy-PC}"
MILHY_PC_REPO="${MILHY_PC_REPO:-/home/milhy777/Develop/RPi}"
STATE_FILE="${STATE_FILE:-$ROOT/.git/rpi-handoff-last-sha}"
RSYNC_EXCLUDES=(
  --exclude '.venv/'
  --exclude '__pycache__/'
  --exclude '*.pyc'
  --exclude '.forensics/'
  --exclude 'conductor/ci/reports/'
  --exclude 'conductor/ci/receipts/'
  --exclude 'playback-memory.json'
  --exclude 'yt-cookies.txt'
)
RECEIPT_DIR="${RECEIPT_DIR:-$ROOT/conductor/ci/receipts}"
REPORT_DIR="${REPORT_DIR:-$ROOT/conductor/ci/reports}"
IMPORT_MAIN_RECEIPT_SCRIPT="${IMPORT_MAIN_RECEIPT_SCRIPT:-$ROOT/tools/import_main_receipt.py}"

has_local_ci_artifacts_for_sha() {
  local sha="$1"
  [[ -n "$(find "$RECEIPT_DIR" -maxdepth 1 -type f -name "${sha}-*.json" 2>/dev/null | head -n 1)" ]] \
    && [[ -n "$(find "$REPORT_DIR" -maxdepth 1 -type f -name "${sha}-*.md" 2>/dev/null | head -n 1)" ]]
}

sync_repo_to_milhy_pc() {
  local head_sha="$1"
  local last_sha=""

  if [[ -f "$STATE_FILE" ]]; then
    last_sha="$(cat "$STATE_FILE")"
  fi

  if [[ "$head_sha" == "$last_sha" ]]; then
    echo "No new commit since last handoff ($head_sha)."
    return 0
  fi

  echo "Syncing $head_sha to $MILHY_PC_HOST:$MILHY_PC_REPO"
  rsync -a --delete "${RSYNC_EXCLUDES[@]}" "$ROOT/" "$MILHY_PC_HOST:$MILHY_PC_REPO/"
  printf '%s\n' "$head_sha" > "$STATE_FILE"
  echo "Handoff queued for $head_sha"
}

import_main_receipt_for_sha() {
  local head_sha="$1"

  if has_local_ci_artifacts_for_sha "$head_sha"; then
    echo "CI receipt and report for $head_sha already present locally."
    return 0
  fi

  if ! command -v gh >/dev/null 2>&1; then
    echo "gh is not available; skipping exact-main receipt import."
    return 0
  fi

  local tree_hash
  tree_hash="$(git rev-parse "${head_sha}^{tree}")"
  if ! python3 "$IMPORT_MAIN_RECEIPT_SCRIPT" "$RECEIPT_DIR" "$REPORT_DIR" "$head_sha" "$tree_hash"; then
    echo "No successful exact-main push CI receipt is available yet for $head_sha."
    return 0
  fi

  echo "Imported local CI receipt for exact main commit $head_sha."
}

main() {
  cd "$ROOT"

  if [[ -n "$(git status --porcelain)" ]]; then
    echo "Working tree dirty; not triggering CI handoff."
    exit 0
  fi

  local head_sha
  head_sha="$(git rev-parse HEAD)"

  sync_repo_to_milhy_pc "$head_sha"
  import_main_receipt_for_sha "$head_sha"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi

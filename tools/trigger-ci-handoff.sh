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
  --exclude '/conductor/ci/reports/'
  --exclude 'playback-memory.json'
  --exclude 'yt-cookies.txt'
)
RECEIPT_DIR="${RECEIPT_DIR:-$ROOT/conductor/ci/receipts}"
REPORT_DIR="${REPORT_DIR:-$ROOT/conductor/ci/reports}"
IMPORT_MAIN_RECEIPT_SCRIPT="${IMPORT_MAIN_RECEIPT_SCRIPT:-$ROOT/tools/import_main_receipt.py}"

has_local_ci_artifacts_for_sha() {
  local sha="$1"
  python3 - "$RECEIPT_DIR" "$ROOT" "$sha" <<'PY'
import json
from pathlib import Path
import sys

receipt_dir, repo_root, expected_sha = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
for receipt_path in sorted(receipt_dir.glob(f"{expected_sha}-*.json"), reverse=True):
    try:
        receipt = json.loads(receipt_path.read_text())
    except (OSError, json.JSONDecodeError):
        continue
    if receipt.get("commit_sha") != expected_sha or receipt.get("source") != "github-actions-main-push":
        continue
    report_value = receipt.get("ci_report")
    if not isinstance(report_value, str) or not report_value:
        continue
    report_path = Path(report_value)
    if not report_path.is_absolute():
        report_path = repo_root / report_path
    try:
        report_text = report_path.read_text()
    except OSError:
        continue
    if any(line.startswith("PASS") for line in report_text.splitlines()):
        print(receipt_path)
        raise SystemExit(0)
raise SystemExit(1)
PY
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
  local candidate_receipt="conductor/ci/receipts/${head_sha}-receipt.json"
  local receipt_filters=(--exclude='/conductor/ci/receipts/***')
  if [[ -f "$ROOT/$candidate_receipt" ]]; then
    receipt_filters=(
      --include='/conductor/'
      --include='/conductor/ci/'
      --include='/conductor/ci/receipts/'
      --include="/$candidate_receipt"
      --exclude='/conductor/ci/receipts/***'
    )
  fi

  rsync -a --delete "${receipt_filters[@]}" "${RSYNC_EXCLUDES[@]}" "$ROOT/" "$MILHY_PC_HOST:$MILHY_PC_REPO/"
  printf '%s\n' "$head_sha" > "$STATE_FILE"
  echo "Handoff queued for $head_sha"
}

import_main_receipt_for_sha() {
  local head_sha="$1"

  if has_local_ci_artifacts_for_sha "$head_sha"; then
    echo "Exact-main CI receipt and its report for $head_sha already present locally."
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

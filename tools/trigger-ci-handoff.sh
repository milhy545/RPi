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
  --exclude 'playback-memory.json'
  --exclude 'yt-cookies.txt'
)
RECEIPT_DIR="${RECEIPT_DIR:-$ROOT/conductor/ci/receipts}"
REPORT_DIR="${REPORT_DIR:-$ROOT/conductor/ci/reports}"

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

select_completed_run_id() {
  local runs_json="$1"
  local head_sha="$2"

  RUNS_JSON="$runs_json" python3 - "$head_sha" <<'PY'
import json
import os
import sys

sha = sys.argv[1]
runs = json.loads(os.environ["RUNS_JSON"])
for run in runs:
    if (
        run.get("databaseId")
        and run.get("headSha") == sha
        and run.get("headBranch") == "main"
        and run.get("event") == "push"
        and run.get("status") == "completed"
        and run.get("conclusion") == "success"
    ):
        print(run["databaseId"])
        break
PY
}

copy_downloaded_artifact_files() {
  local download_dir="$1"
  local copied=0
  mkdir -p "$RECEIPT_DIR" "$REPORT_DIR"

  while IFS= read -r -d '' file; do
    case "$(basename "$file")" in
      *.json)
        cp -f "$file" "$RECEIPT_DIR/"
        copied=1
        ;;
      *.md)
        cp -f "$file" "$REPORT_DIR/"
        copied=1
        ;;
    esac
  done < <(find "$download_dir" -type f -print0)

  if [[ $copied -eq 1 ]]; then
    return 0
  fi
  return 1
}

download_ci_artifacts_for_sha() {
  local head_sha="$1"

  if has_local_ci_artifacts_for_sha "$head_sha"; then
    echo "CI artifacts for $head_sha already present locally."
    return 0
  fi

  if ! command -v gh >/dev/null 2>&1; then
    echo "gh is not available; skipping CI artifact sync."
    return 0
  fi

  local runs_json run_id download_dir
  if ! runs_json="$(gh run list --commit "$head_sha" --workflow ci.yml --json databaseId,headSha,headBranch,event,status,conclusion 2>/dev/null)"; then
    echo "No GitHub Actions run list available yet for $head_sha."
    return 0
  fi

  run_id="$(select_completed_run_id "$runs_json" "$head_sha")"
  if [[ -z "$run_id" ]]; then
    echo "No completed GitHub Actions push run yet for $head_sha."
    return 0
  fi

  download_dir="$(mktemp -d)"
  trap 'rm -rf "$download_dir"' RETURN

  if ! gh run download "$run_id" -n ci-receipt -n ci-report-ubuntu -D "$download_dir"; then
    echo "Failed to download GitHub Actions artifacts for $head_sha (run $run_id)." >&2
    return 1
  fi

  if ! copy_downloaded_artifact_files "$download_dir"; then
    echo "Downloaded artifacts for $head_sha did not contain receipt/report files." >&2
    return 1
  fi

  echo "Downloaded CI artifacts for $head_sha from GitHub Actions run $run_id."
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
  download_ci_artifacts_for_sha "$head_sha"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi

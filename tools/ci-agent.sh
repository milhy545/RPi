#!/usr/bin/env bash
# ci-agent.sh — Milhy-PC CI gateway for RPi Dashboard.
# Default mode validates the local checked-out repository and pushes to GitHub only on success.
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SOURCE_REMOTE="${SOURCE_REMOTE:-local}"   # local or a git remote name
TARGET_REMOTE="${TARGET_REMOTE:-origin}"
BRANCH="${BRANCH:-master}"
POLL_SECONDS="${POLL_SECONDS:-0}"
REPORT_DIR="${REPORT_DIR:-conductor/ci/reports}"
STATE_FILE="${STATE_FILE:-.git/rpi-ci-agent-last-sha}"
mkdir -p "$REPORT_DIR"

notify_fail() {
  local msg="$1"
  echo "CI FAILURE: $msg"
  if command -v notify-send >/dev/null 2>&1; then
    notify-send "RPi CI failed" "$msg" || true
  fi
}

latest_report() {
  find "$REPORT_DIR" -maxdepth 1 -type f -name '*.md' -printf '%T@ %p\n' 2>/dev/null \
    | sort -nr \
    | awk 'NR==1 {sub(/^[^ ]+ /, ""); print}'
}

prepare_candidate() {
  if [[ "$SOURCE_REMOTE" == "local" ]]; then
    git rev-parse HEAD
    return 0
  fi

  git fetch "$SOURCE_REMOTE" "$BRANCH"
  local source_sha
  source_sha="$(git rev-parse FETCH_HEAD)"

  if [[ -n "$(git status --porcelain)" ]]; then
    local backup
    backup="ci-dirty-backup-$(date +%Y%m%d-%H%M%S)"
    echo "Dirty worktree detected; stashing as $backup"
    git stash push -u -m "$backup" >/dev/null
  fi

  echo "Checking out candidate $source_sha"
  git checkout -B "$BRANCH" FETCH_HEAD
  printf '%s\n' "$source_sha"
}

run_once() {
  echo "== RPi CI agent run: $(date -Is) =="
  local source_sha
  if ! source_sha="$(prepare_candidate)"; then
    notify_fail "Could not prepare CI candidate."
    return 1
  fi

  local last_sha=""
  [[ -f "$STATE_FILE" ]] && last_sha="$(cat "$STATE_FILE")"
  if [[ "$POLL_SECONDS" != "0" && "$source_sha" == "$last_sha" ]]; then
    echo "No new local commit ($source_sha)."
    return 0
  fi

  if tools/run-ci.sh; then
    echo "CI passed for $source_sha. Pushing to $TARGET_REMOTE/$BRANCH"
    if GIT_TERMINAL_PROMPT=0 git push "$TARGET_REMOTE" "$BRANCH:$BRANCH"; then
      printf '%s\n' "$source_sha" > "$STATE_FILE"
      echo "Pushed $source_sha to GitHub remote $TARGET_REMOTE."
      return 0
    fi
    local report
    report="$(latest_report || true)"
    notify_fail "Commit $source_sha passed CI but GitHub push failed. Check GitHub authentication. Report: ${report:-none}"
    return 1
  fi

  local report
  report="$(latest_report || true)"
  notify_fail "Commit $source_sha failed. Report: ${report:-none}"
  return 1
}

if [[ "$POLL_SECONDS" == "0" ]]; then
  run_once
  exit $?
fi

while true; do
  if ! run_once; then
    echo "CI failed; keeping agent alive."
  fi
  sleep "$POLL_SECONDS"
done

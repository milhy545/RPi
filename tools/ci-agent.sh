#!/usr/bin/env bash
# ci-agent.sh — Milhy-PC CI gateway for RPi Dashboard.
# Default mode validates the local checked-out repository and pushes to GitHub only on success.
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SOURCE_REMOTE="${SOURCE_REMOTE:-local}"   # local or a git remote name
TARGET_REMOTE="${TARGET_REMOTE:-origin}"
BRANCH_OVERRIDE="${BRANCH:-}"
CURRENT_BRANCH="$(git branch --show-current 2>/dev/null || git rev-parse --abbrev-ref HEAD 2>/dev/null || echo master)"
BRANCH="${BRANCH:-$CURRENT_BRANCH}"
POLL_SECONDS="${POLL_SECONDS:-0}"
REPORT_DIR="${REPORT_DIR:-conductor/ci/reports}"
STATE_FILE="${STATE_FILE:-.git/rpi-ci-agent-last-sha}"
mkdir -p "$REPORT_DIR"

refresh_branch() {
  if [[ -z "$BRANCH_OVERRIDE" ]]; then
    BRANCH="$(git branch --show-current 2>/dev/null || git rev-parse --abbrev-ref HEAD 2>/dev/null || echo master)"
  fi
}

remote_has_commit() {
  local source_sha="$1"
  local remote_sha
  remote_sha="$(git ls-remote "$TARGET_REMOTE" "refs/heads/$BRANCH" 2>/dev/null | awk 'NR == 1 { print $1 }')"
  [[ -n "$remote_sha" && "$remote_sha" == "$source_sha" ]]
}

notify_fail() {
  local msg="$1"
  echo "CI FAILURE: $msg"
  if command -v notify-send >/dev/null 2>&1; then
    notify-send "RPi CI failed" "$msg" || true
  fi
}

latest_report() {
  local expected_sha="${1:-}"
  local candidate

  while IFS= read -r candidate; do
    [[ -n "$candidate" && -s "$candidate" ]] || continue
    grep -qx 'PASS' "$candidate" || continue
    if [[ -n "$expected_sha" ]] && ! grep -Fqx -- "- Commit: $expected_sha" "$candidate"; then
      continue
    fi
    printf '%s\n' "$candidate"
    return 0
  done < <(
    find "$REPORT_DIR" -maxdepth 1 -type f -name '*.md' -printf '%T@ %p\n' 2>/dev/null \
      | sort -nr \
      | sed 's/^[^ ]* //'
  )

  return 1
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
  refresh_branch
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

  if [[ "$POLL_SECONDS" != "0" ]] && remote_has_commit "$source_sha"; then
    echo "Commit $source_sha is already present on $TARGET_REMOTE/$BRANCH; recording it as processed."
    printf '%s\n' "$source_sha" > "$STATE_FILE"
    return 0
  fi

  if tools/run-ci.sh; then
    echo "CI passed for $source_sha. Pushing to $TARGET_REMOTE/$BRANCH"
    if GIT_TERMINAL_PROMPT=0 git push "$TARGET_REMOTE" "$BRANCH:$BRANCH"; then
      echo "Pushed $source_sha to GitHub remote $TARGET_REMOTE."
      # Discover GitHub Actions run for this SHA with bounded retries and strict matching
      MAX_RETRIES=12
      RETRY=0
      GH_RUN_ID=""
      while [[ $RETRY -lt $MAX_RETRIES && -z $GH_RUN_ID ]]; do
        # List runs for the commit; capture errors but continue retries
        if ! GH_RUN_JSON=$(gh run list --commit "$source_sha" --workflow ci.yml --json databaseId,url,headSha 2>&1); then
          notify_fail "gh run list command failed for SHA $source_sha: $GH_RUN_JSON"
          GH_RUN_JSON="[]"
        fi
        # Accept empty JSON array as no run yet
        if [[ -z "$GH_RUN_JSON" ]]; then
          GH_RUN_JSON="[]"
        fi
        GH_RUN_ID=$(python3 -c "import json, sys; runs=json.load(sys.stdin); target='$source_sha'; print(next((r.get('databaseId') for r in runs if r.get('headSha')==target), ''))" <<<"$GH_RUN_JSON")
        if [[ -n $GH_RUN_ID ]]; then
          break
        fi
        RETRY=$((RETRY+1))
        sleep 5
      done
      if [[ -z $GH_RUN_ID ]]; then
        notify_fail "No GitHub Actions run found for SHA $source_sha after $MAX_RETRIES retries"
        return 1
      fi
      # Wait for run completion with a 600s timeout
      if ! timeout 600 gh run watch "$GH_RUN_ID" --exit-status; then
        notify_fail "GitHub Actions run $GH_RUN_ID did not succeed within timeout"
        return 1
      fi
      GH_RUN_URL=$(gh run view "$GH_RUN_ID" --json url --jq '.url')
      # Emit CI report only if it exists and is non‑empty
      CI_REPORT=$(latest_report "$source_sha")
      if [[ -z "$CI_REPORT" ]]; then
        notify_fail "CI report not found after successful run"
        return 1
      fi
      echo "CI_REPORT=$CI_REPORT"
      echo "GITHUB_ACTIONS_URL=$GH_RUN_URL"
      # Update state file only after successful CI run
      printf '%s\n' "$source_sha" > "$STATE_FILE"
      return 0
    fi
    local report
    report="$(latest_report "$source_sha")"
    if [[ -z "$report" ]]; then
      notify_fail "CI report not found after push failure"
      return 1
    fi
    notify_fail "Commit $source_sha passed CI but GitHub push failed. Check GitHub authentication. Report: ${report:-none}"
    return 1
  fi

  local report
  report="$(latest_report "$source_sha" || true)"
  notify_fail "Commit $source_sha failed. Report: ${report:-none}"
  return 1
}

main() {
  if [[ "$POLL_SECONDS" == "0" ]]; then
    run_once
    return $?
  fi

  while true; do
    if ! run_once; then
      echo "CI failed; keeping agent alive."
    fi
    sleep "$POLL_SECONDS"
  done
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi

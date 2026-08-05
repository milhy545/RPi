#!/usr/bin/env bash
# ci-agent.sh — Milhy-PC CI gateway for RPi Dashboard.
# Default mode validates the local checked-out repository and pushes to GitHub only on success.
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SOURCE_REMOTE="${SOURCE_REMOTE:-local}"   # local or a git remote name
TARGET_REMOTE="${TARGET_REMOTE:-origin}"
BRANCH_OVERRIDE="${BRANCH:-}"
CURRENT_BRANCH="$(git symbolic-ref --quiet --short HEAD 2>/dev/null || true)"
BRANCH="${BRANCH:-$CURRENT_BRANCH}"
POLL_SECONDS="${POLL_SECONDS:-0}"
REPORT_DIR="${REPORT_DIR:-conductor/ci/reports}"
_resolve_state_path() {
  local gitpath
  gitpath="$(git rev-parse --git-path "rpi-ci-agent-last-sha" 2>/dev/null)" || true
  if [[ -n "$gitpath" ]]; then
    printf '%s' "$gitpath"
  else
    printf '%s' ".git/rpi-ci-agent-last-sha"
  fi
}

STATE_FILE="${STATE_FILE:-}"
if [[ -z "$STATE_FILE" ]]; then
  STATE_FILE="$(_resolve_state_path)"
fi
mkdir -p "$REPORT_DIR"
mkdir -p "$(dirname "$STATE_FILE")"

refresh_branch() {
  if [[ -z "$BRANCH_OVERRIDE" ]]; then
    local current_branch
    if ! current_branch="$(git symbolic-ref --quiet --short HEAD 2>/dev/null)" || [[ -z "$current_branch" ]]; then
      echo "Cannot determine a branch from detached HEAD." >&2
      return 1
    fi
    BRANCH="$current_branch"
  fi
}

remote_has_commit() {
  local source_sha="$1"
  local remote_sha
  if ! git fetch --quiet --no-tags "$TARGET_REMOTE" "refs/heads/$BRANCH" 2>/dev/null; then
    return 1
  fi
  remote_sha="$(git rev-parse FETCH_HEAD 2>/dev/null)"
  [[ -n "$remote_sha" ]] && git merge-base --is-ancestor "$source_sha" "$remote_sha"
}

notify_fail() {
  local msg="$1"
  echo "CI FAILURE: $msg"
  if command -v notify-send >/dev/null 2>&1; then
    notify-send "RPi CI failed" "$msg" || true
  fi
}

dispatch_ci() {
  if [[ "$BRANCH" == "main" ]]; then
    return 0
  fi
  if ! gh workflow run ci.yml --ref "$BRANCH"; then
    notify_fail "Failed to dispatch CI workflow for branch $BRANCH"
    return 1
  fi
  echo "Dispatched ci.yml for branch $BRANCH"
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
    # For local source, refuse if worktree is dirty (fail-loud preservation)
    if [[ -n "$(git status --porcelain)" ]]; then
      echo "FATAL: Dirty worktree detected. Refusing to modify/stash state per binding contract." >&2
      echo "Preserve dirty changes manually, then retry." >&2
      return 1
    fi
    git rev-parse HEAD
    return 0
  fi

  git fetch "$SOURCE_REMOTE" "$BRANCH"
  local source_sha
  source_sha="$(git rev-parse FETCH_HEAD)"

  # For remote source, also refuse if current worktree is dirty
  if [[ -n "$(git status --porcelain)" ]]; then
    echo "FATAL: Dirty worktree detected. Refusing to modify/stash state per binding contract." >&2
    echo "Preserve dirty changes manually, then retry." >&2
    return 1
  fi

  echo "Checking out candidate $source_sha" >&2
  git checkout -B "$BRANCH" FETCH_HEAD
  printf '%s\n' "$source_sha"
}

run_once() {
  if ! refresh_branch; then
    notify_fail "Could not determine the checked-out branch."
    return 1
  fi
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

  # Enforce Milhy-PC sole push gateway contract
  local host_name
  host_name="$(hostname 2>/dev/null | tr '[:upper:]' '[:lower:]' || echo "unknown")"
  if [[ "$host_name" == *"rpi"* ]]; then
    notify_fail "FATAL: RPi host is forbidden from executing git push. Milhy-PC is sole push gateway."
    return 1
  fi

  # Milhy-PC gateway must use milhy-full profile (enforces full backend/lint/type/security/E2E)
  if CI_PROFILE="${CI_PROFILE:-milhy-full}" tools/run-ci.sh; then
    echo "CI passed for $source_sha under profile ${CI_PROFILE:-milhy-full}."

    # EVIDENCE GATE: Verify Playwright/E2E artifacts and RPi candidate evidence exist
    E2E_ARTIFACTS_DIR="tests/e2e/results"
    RPI_EVIDENCE_DIR="conductor/ci/receipts"

    # Check for E2E artifacts (Playwright results)
    if [[ "$PROFILE" == "milhy-full" ]]; then
      if [[ ! -d "$E2E_ARTIFACTS_DIR" || -z "$(ls -A "$E2E_ARTIFACTS_DIR" 2>/dev/null)" ]]; then
        notify_fail "EVIDENCE GATE FAILED: No Playwright/E2E artifacts found in $E2E_ARTIFACTS_DIR for SHA $source_sha. Push blocked."
        return 1
      fi
      echo "E2E artifacts verified: $E2E_ARTIFACTS_DIR"
    fi

    # Check for exact-SHA RPi candidate evidence (atomic receipt)
    if [[ ! -d "$RPI_EVIDENCE_DIR" || -z "$(find "$RPI_EVIDENCE_DIR" -name "*$source_sha*" -type f 2>/dev/null)" ]]; then
      notify_fail "EVIDENCE GATE FAILED: No exact-SHA RPi candidate receipt found in $RPI_EVIDENCE_DIR for SHA $source_sha. Push blocked."
      return 1
    fi
    echo "RPi candidate evidence verified for SHA $source_sha"

    echo "Pushing to $TARGET_REMOTE/$BRANCH"
    if GIT_TERMINAL_PROMPT=0 git push "$TARGET_REMOTE" "$BRANCH:$BRANCH"; then
      echo "Pushed $source_sha to GitHub remote $TARGET_REMOTE."
      if ! dispatch_ci; then
        return 1
      fi
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

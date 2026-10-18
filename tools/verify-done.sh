#!/usr/bin/env bash
# verify-done.sh — AGENT MANDATORY SELF-CHECK before claiming "done".
#
# This script MUST be called by the agent before saying "hotovo" / "done".
# Exit code 0 = truly done. Exit code 1 = NOT done, agent must not claim success.
#
# SAFETY RULE:
#   The agent MUST NOT say "done", "hotovo", "finished", or "completed"
#   unless this script exits with code 0.
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RECEIPT_DIR="${RECEIPT_DIR:-conductor/ci/receipts}"
REPORT_DIR="${REPORT_DIR:-conductor/ci/reports}"
ERRORS=0

err() { echo "FAIL: $*" >&2; ERRORS=$((ERRORS + 1)); }
ok()  { echo "OK: $*"; }
skip(){ echo "SKIP: $*"; }

# ─── Check 1: Git status ────────────────────────────────────────────────────
echo "=== Check 1: Git status ==="
HEAD_SHA="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
HEAD_TREE="$(git rev-parse 'HEAD^{tree}' 2>/dev/null || echo unknown)"
CURRENT_BRANCH="$(git branch --show-current 2>/dev/null || echo unknown)"

if [[ "$HEAD_SHA" == "unknown" ]]; then
  err "Cannot determine HEAD SHA"
else
  ok "HEAD=$HEAD_SHA branch=$CURRENT_BRANCH"
fi

# ─── Check 2: Working tree cleanliness ──────────────────────────────────────
echo "=== Check 2: Working tree ==="
if DIRTY_STATUS="$(git status --short --untracked-files=all 2>/dev/null)"; then
  if [[ -n "$DIRTY_STATUS" ]]; then
    err "Working tree has uncommitted changes:"
    printf '%s\n' "$DIRTY_STATUS" >&2
  else
    ok "Working tree is clean"
  fi
else
  err "Cannot determine working tree status"
fi

# ─── Check 3: Receipt exists for current HEAD ───────────────────────────────
echo "=== Check 3: Receipt for HEAD ==="
EXPECTED_RECEIPT_SOURCE="github-actions-main-push"
RECEIPT_EXACT_SHA=false
if [[ "${GITHUB_ACTIONS:-}" == "true" && "${GITHUB_EVENT_NAME:-}" == "pull_request" ]]; then
  EXPECTED_RECEIPT_SOURCE="github-actions-pull-request"
  RECEIPT_EXACT_SHA=true
fi

lookup_receipt() {
  if [[ "$RECEIPT_EXACT_SHA" == true ]]; then
    python3 tools/receipt_lookup.py "$RECEIPT_DIR" "$HEAD_SHA" "$HEAD_TREE" \
      --source "$EXPECTED_RECEIPT_SOURCE" --exact-sha
  else
    python3 tools/receipt_lookup.py "$RECEIPT_DIR" "$HEAD_SHA" "$HEAD_TREE" \
      --source "$EXPECTED_RECEIPT_SOURCE"
  fi
}

RECEIPT="$(lookup_receipt)"
if [[ -z "$RECEIPT" && "$EXPECTED_RECEIPT_SOURCE" == "github-actions-main-push" ]]; then
  echo "No local source receipt matches; checking exact-main GitHub push CI..."
  if python3 tools/import_main_receipt.py "$RECEIPT_DIR" "$REPORT_DIR" "$HEAD_SHA" "$HEAD_TREE"; then
    RECEIPT="$(lookup_receipt)"
  fi
fi
if [[ -z "$RECEIPT" ]]; then
  err "No receipt found for HEAD=$HEAD_SHA or tree=$HEAD_TREE in $RECEIPT_DIR"
  echo "  A valid CI receipt for this commit or an identical tree is required." >&2
  echo "  The agent MUST NOT claim 'done' without a receipt." >&2
else
  # Validate receipt contents with explicit failure handling
  if ! RECEIPT_STATUS=$(python3 -c "import json, sys; print(json.load(open('$RECEIPT')).get('status',''))"); then
    err "Failed to read receipt status from $RECEIPT"
    RECEIPT_STATUS=""
  fi
  if [[ -z "$RECEIPT_STATUS" ]]; then
    err "Failed to read receipt status from $RECEIPT"
  fi
  if ! RECEIPT_SHA=$(python3 -c "import json, sys; print(json.load(open('$RECEIPT')).get('commit_sha',''))"); then
    err "Failed to read receipt commit_sha from $RECEIPT"
    RECEIPT_SHA=""
  fi
  if [[ -z "$RECEIPT_SHA" ]]; then
    err "Failed to read receipt commit_sha from $RECEIPT"
  fi
  if ! RECEIPT_TREE=$(python3 -c "import json, sys; print(json.load(open('$RECEIPT')).get('tree_hash',''))"); then
    err "Failed to read receipt tree_hash from $RECEIPT"
    RECEIPT_TREE=""
  fi

  if [[ -z "$RECEIPT_STATUS" ]]; then
    err "Receipt missing or unreadable"
  elif [[ "$RECEIPT_STATUS" != "done" ]]; then
    err "Receipt status is '$RECEIPT_STATUS' (expected 'done')"
  elif [[ -z "$RECEIPT_SHA" ]]; then
    err "Receipt missing commit_sha"
  elif [[ "$RECEIPT_SHA" != "$HEAD_SHA" && "$RECEIPT_TREE" != "$HEAD_TREE" ]]; then
    err "Receipt neither matches HEAD SHA nor tree hash"
  else
    if [[ "$RECEIPT_SHA" == "$HEAD_SHA" ]]; then
      ok "Valid receipt for HEAD SHA: $RECEIPT"
    else
      ok "Valid receipt for identical Git tree after rebase: $RECEIPT"
    fi
    # Additional checks for ci_report and actions_url
    if ! CI_REPORT=$(python3 -c "import json, sys; print(json.load(open('$RECEIPT')).get('ci_report',''))"); then
      err "Failed to read receipt ci_report from $RECEIPT"
      CI_REPORT=""
    fi
    if [[ -z "$CI_REPORT" || "$CI_REPORT" == "null" ]]; then
      err "Receipt ci_report is empty or missing"
    elif [[ ! -f "$CI_REPORT" ]]; then
      err "ci_report file does not exist at $CI_REPORT"
    elif ! grep -q '^PASS' "$CI_REPORT"; then
      err "ci_report file $CI_REPORT does not contain PASS line"
    fi
    if ! ACTIONS_URL=$(python3 -c "import json, sys; print(json.load(open('$RECEIPT')).get('actions_url',''))"); then
      err "Failed to read receipt actions_url from $RECEIPT"
      ACTIONS_URL=""
    fi
    if [[ -z "$ACTIONS_URL" || "$ACTIONS_URL" == "null" ]]; then
      err "Receipt actions_url is empty or missing"
    elif [[ "$ACTIONS_URL" != https://* ]]; then
      err "Receipt actions_url is not an https URL"
    fi
  fi
fi

# ─── Check 5: Milhy-PC mirror sync ──────────────────────────────────────────
echo "=== Check 5: Milhy-PC mirror ==="
MILHY_PC_HOST="${MILHY_PC_HOST:-Milhy-PC}"
MILHY_PC_REPO="${MILHY_PC_REPO:-/home/milhy777/Develop/RPi}"

if ! ssh -o BatchMode=yes -o ConnectTimeout=5 "$MILHY_PC_HOST" true 2>/dev/null; then
  skip "Milhy-PC unreachable (cannot verify mirror sync)"
else
  # shellcheck disable=SC2029 # Intentional client-side expansion of configured host/path.
  REMOTE_SHA="$(ssh "$MILHY_PC_HOST" "cd '$MILHY_PC_REPO' && git rev-parse HEAD 2>/dev/null" 2>/dev/null || echo unknown)"
  if [[ "$REMOTE_SHA" == "$HEAD_SHA" ]]; then
    ok "Milhy-PC mirror matches HEAD: $REMOTE_SHA"
  else
    err "Milhy-PC mirror SHA mismatch (expected $HEAD_SHA, got $REMOTE_SHA)"
  fi
fi

# ─── Check 6: GitHub remote state ───────────────────────────────────────────
echo "=== Check 6: GitHub remote ==="
if [[ -z "$CURRENT_BRANCH" ]]; then
  if [[ "${GITHUB_ACTIONS:-}" == "true" && "${GITHUB_SHA:-}" == "$HEAD_SHA" && -n "${GITHUB_REF:-}" ]]; then
    skip "Detached GitHub Actions checkout matches GITHUB_SHA and GITHUB_REF"
  else
    err "Detached checkout is not verified by GitHub Actions; pushed state cannot be confirmed"
  fi
elif ! git remote get-url origin >/dev/null 2>&1; then
  skip "No origin remote configured"
else
  REMOTE_PUSHED="$(git log "origin/$CURRENT_BRANCH"..HEAD --oneline 2>/dev/null | wc -l | tr -d ' ')"
  if [[ "$REMOTE_PUSHED" -eq 0 ]]; then
    ok "HEAD is pushed to origin/$CURRENT_BRANCH"
  else
    err "HEAD has $REMOTE_PUSHED unpushed commit(s) to origin/$CURRENT_BRANCH"
  fi
fi

# ─── Check 7: No runtime artifacts in last commit ───────────────────────────
echo "=== Check 7: Runtime artifacts ==="
if [[ -n "${VERIFY_BASE_SHA:-}" && "$VERIFY_BASE_SHA" != "0000000000000000000000000000000000000000" ]]; then
  if ! ARTIFACTS_IN_RANGE="$(git diff --name-only "$VERIFY_BASE_SHA" HEAD 2>/dev/null)"; then
    err "Cannot inspect runtime artifacts between $VERIFY_BASE_SHA and HEAD"
    ARTIFACTS_IN_RANGE=""
  fi
elif git rev-parse --verify 'HEAD^' >/dev/null 2>&1; then
  if ! ARTIFACTS_IN_RANGE="$(git diff --name-only HEAD^ HEAD 2>/dev/null)"; then
    err "Cannot inspect runtime artifacts in the HEAD commit"
    ARTIFACTS_IN_RANGE=""
  fi
else
  if ! ARTIFACTS_IN_RANGE="$(git diff-tree --root --no-commit-id --name-only -r HEAD 2>/dev/null)"; then
    err "Cannot inspect runtime artifacts in the root commit"
    ARTIFACTS_IN_RANGE=""
  fi
fi
ARTIFACTS_IN_RANGE="$(printf '%s\n' "$ARTIFACTS_IN_RANGE" | grep -v '\.gitkeep$' | grep -v 'conductor/ci/receipts/.*\.json$' | grep -E '\.(pyc)$|__pycache__|\.forensics/|playback-memory\.json|yt-cookies\.txt|conductor/ci/reports/|conductor/ci/receipts/' || true)"
if [[ -n "$ARTIFACTS_IN_RANGE" ]]; then
  err "Runtime artifacts found in the verified commit range:"
  echo "$ARTIFACTS_IN_RANGE" >&2
else
  ok "No runtime artifacts in HEAD commit"
fi

# ─── Check 8: Forbid forbidden strings ──────────────────────────────────────
echo "=== Check 8: Forbidden strings ==="
if git show HEAD -- webserver.py tui.py mode_switcher.py keys2mpv.py 2>/dev/null | grep -E 'GFN-TV|killall mpv|pkill mpv'; then
  err "Forbidden strings found in HEAD commit source files"
else
  ok "No forbidden strings in HEAD"
fi

# ─── Final verdict ──────────────────────────────────────────────────────────
echo ""
echo "==============================="
if [[ $ERRORS -eq 0 ]]; then
  echo "VERIFY-DONE: PASS — agent may claim 'done'"
  echo "==============================="
  exit 0
else
  echo "VERIFY-DONE: FAIL ($ERRORS error(s)) — agent MUST NOT claim 'done'"
  echo "==============================="
  exit 1
fi

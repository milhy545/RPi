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
BRANCH="$(git branch --show-current 2>/dev/null || echo detached)"

if [[ "$HEAD_SHA" == "unknown" ]]; then
  err "Cannot determine HEAD SHA"
else
  ok "HEAD=$HEAD_SHA branch=$BRANCH"
fi

# ─── Check 2: Working tree cleanliness ──────────────────────────────────────
echo "=== Check 2: Working tree ==="
DIRTY="$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
if [[ "$DIRTY" -gt 0 ]]; then
  err "Working tree has $DIRTY uncommitted changes"
else
  ok "Working tree is clean"
fi

# ─── Check 3: Receipt exists for current HEAD ───────────────────────────────
echo "=== Check 3: Receipt for HEAD ==="
RECEIPT="$(find "$RECEIPT_DIR" -name "${HEAD_SHA}-*.json" -type f 2>/dev/null | sort -r | head -1 || true)"
if [[ -z "$RECEIPT" ]]; then
  err "No receipt found for HEAD=$HEAD_SHA in $RECEIPT_DIR"
  echo "  This means finish-track.sh was not run or it failed." >&2
  echo "  The agent MUST NOT claim 'done' without a receipt." >&2
else
  # Validate receipt contents
  RECEIPT_STATUS="$(python3 -c "import json; print(json.load(open('$RECEIPT'))['status'])" 2>/dev/null || echo corrupt)"
  RECEIPT_SHA="$(python3 -c "import json; print(json.load(open('$RECEIPT'))['commit_sha'])" 2>/dev/null || echo unknown)"

  if [[ "$RECEIPT_STATUS" != "done" ]]; then
    err "Receipt status is '$RECEIPT_STATUS' (expected 'done')"
  elif [[ "$RECEIPT_SHA" != "$HEAD_SHA" ]]; then
    err "Receipt SHA ($RECEIPT_SHA) does not match HEAD ($HEAD_SHA)"
  else
    ok "Valid receipt: $RECEIPT"
  fi
fi

# ─── Check 4: CI report exists for HEAD ─────────────────────────────────────
echo "=== Check 4: CI report ==="
REPORT="$(find "$REPORT_DIR" -name "${HEAD_SHA}-*.md" -type f 2>/dev/null | sort -r | head -1 || true)"
if [[ -z "$REPORT" ]]; then
  err "No CI report found for HEAD=$HEAD_SHA"
else
  if grep -q "^PASS" "$REPORT" 2>/dev/null; then
    ok "CI report PASS: $REPORT"
  elif grep -q "^FAILURES" "$REPORT" 2>/dev/null; then
    err "CI report shows FAILURES: $REPORT"
  else
    ok "CI report exists (final line unclear): $REPORT"
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
if ! git remote get-url origin >/dev/null 2>&1; then
  skip "No origin remote configured"
else
  REMOTE_PUSHED="$(git log "origin/$BRANCH"..HEAD --oneline 2>/dev/null | wc -l | tr -d ' ')"
  if [[ "$REMOTE_PUSHED" -eq 0 ]]; then
    ok "HEAD is pushed to origin/$BRANCH"
  else
    err "HEAD has $REMOTE_PUSHED unpushed commit(s) to origin/$BRANCH"
  fi
fi

# ─── Check 7: No runtime artifacts in last commit ───────────────────────────
echo "=== Check 7: Runtime artifacts ==="
ARTIFACTS_IN_COMMIT="$(git diff-tree --no-commit-id --name-only -r HEAD 2>/dev/null | grep -E '\.(pyc)$|__pycache__|\.forensics/|playback-memory\.json|yt-cookies\.txt|conductor/ci/reports/|conductor/ci/receipts/' || true)"
if [[ -n "$ARTIFACTS_IN_COMMIT" ]]; then
  err "Runtime artifacts found in HEAD commit:"
  echo "$ARTIFACTS_IN_COMMIT" >&2
else
  ok "No runtime artifacts in HEAD commit"
fi

# ─── Check 8: Forbid forbidden strings ──────────────────────────────────────
echo "=== Check 8: Forbidden strings ==="
if git show HEAD -- webserver_8099.py tui.py mode_switcher.py keys2mpv.py 2>/dev/null | grep -E 'GFN-TV|killall mpv|pkill mpv'; then
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

#!/usr/bin/env bash
# finish-track.sh — safe local finish/commit handoff to Milhy-PC CI gateway.
#
# SAFETY RULES:
#   1. CI must PASS before commit is created. No exceptions.
#   2. Commit SHA is recorded BEFORE commit and verified AFTER.
#   3. Atomic receipt is created ONLY on full success. No receipt = not done.
#   4. Any single step failure aborts the entire pipeline immediately.
#   5. The agent MUST NOT claim "done" without an on-disk receipt.
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RECEIPT_DIR="${RECEIPT_DIR:-conductor/ci/receipts}"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
mkdir -p "$RECEIPT_DIR"

usage() {
  cat <<'USAGE'
Usage: tools/finish-track.sh "commit message"

Runs local CI, creates a safety stash snapshot if needed, commits current changes,
syncs the repository to Milhy-PC, and triggers the Milhy-PC CI gateway. It does not push directly to GitHub.

Environment:
  MILHY_PC_HOST     SSH host for Milhy-PC (default: Milhy-PC)
  MILHY_PC_REPO     Repo path on Milhy-PC (default: /home/milhy777/Develop/RPi)
  TARGET_BRANCH     Branch to validate/push (default: master)

SAFETY:
  An atomic receipt is written ONLY when every step succeeds.
  If any step fails, the receipt is never created.
  The agent MUST NOT claim "done" without a valid receipt file.
USAGE
}

# ─── Step 0: Validate environment ───────────────────────────────────────────
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then usage; exit 0; fi
if [[ $# -lt 1 ]]; then usage >&2; exit 2; fi

MSG="$1"
MILHY_PC_HOST="${MILHY_PC_HOST:-Milhy-PC}"
MILHY_PC_REPO="${MILHY_PC_REPO:-/home/milhy777/Develop/RPi}"
TARGET_BRANCH="${TARGET_BRANCH:-master}"

if [[ -z "$MSG" ]]; then
  echo "FATAL: commit message must not be empty" >&2
  exit 2
fi

# ─── Step 1: Safety stash snapshot ──────────────────────────────────────────
SNAP="pre-finish-track-$(date +%Y%m%d-%H%M%S)"
echo "Creating safety stash snapshot: $SNAP"
git stash push -u -m "$SNAP" >/dev/null || {
  echo "FATAL: git stash push failed — cannot create safety snapshot" >&2
  exit 1
}
# Re-apply immediately; stash remains as recoverable checkpoint.
if ! git stash apply --index 'stash@{0}' >/dev/null 2>&1; then
  if ! git stash apply 'stash@{0}' >/dev/null 2>&1; then
    echo "FATAL: git stash apply failed after stash — rollback via: git stash pop" >&2
    exit 1
  fi
fi
echo "Safety snapshot $SNAP created."

# ─── Step 2: Record pre-commit state ────────────────────────────────────────
PRE_COMMIT_SHA="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
PRE_TREE_HASH="$(git write-tree 2>/dev/null || echo unknown)"
PRE_DIFF_HASH="$(git diff --stat 2>/dev/null | sha256sum | cut -d' ' -f1 || echo unknown)"
echo "Pre-commit state: SHA=$PRE_COMMIT_SHA TREE=$PRE_TREE_HASH DIFF=$PRE_DIFF_HASH"

# ─── Step 3: Run local CI (must PASS) ───────────────────────────────────────
echo "Running local CI..."
if ! tools/run-ci.sh; then
  echo "FATAL: local CI failed — no commit created, no receipt generated" >&2
  exit 1
fi

# ─── Step 4: Verify no forbidden regressions ────────────────────────────────
echo "Checking for forbidden patterns..."
if grep -nE 'GFN-TV|killall mpv|pkill mpv' webserver_8099.py tui.py mode_switcher.py keys2mpv.py 2>/dev/null; then
  echo "FATAL: forbidden regression strings found in source files — fix before committing" >&2
  exit 1
fi

# ─── Step 5: Verify no runtime artifacts are staged ──────────────────────────
echo "Checking for runtime artifacts..."
ARTIFACT_PATTERNS=(
  '*.pyc'
  '.venv/'
  '__pycache__/'
  '.forensics/'
  'playback-memory.json'
  'yt-cookies.txt'
  'conductor/ci/reports/'
  'conductor/ci/receipts/'
)
for pat in "${ARTIFACT_PATTERNS[@]}"; do
  if git status --porcelain | grep -q "^A.*$pat"; then
    echo "FATAL: runtime artifact matched '$pat' is staged for commit — fix .gitignore" >&2
    git status --porcelain | grep "^A.*$pat" >&2
    exit 1
  fi
done

# ─── Step 6: Commit ─────────────────────────────────────────────────────────
echo "Committing..."
git add -A

# Verify something is actually staged
if git diff --cached --quiet 2>/dev/null; then
  echo "WARNING: nothing staged after git add — skipping commit"
else
  if ! git commit -m "$MSG"; then
    echo "FATAL: git commit failed — rolling back staging area" >&2
    git reset HEAD >/dev/null 2>&1 || true
    exit 1
  fi
fi

# ─── Step 7: Verify commit landed correctly ──────────────────────────────────
POST_COMMIT_SHA="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
POST_TREE_HASH="$(git write-tree 2>/dev/null || echo unknown)"

if [[ "$POST_COMMIT_SHA" == "$PRE_COMMIT_SHA" && "$POST_TREE_HASH" == "$PRE_TREE_HASH" ]]; then
  echo "WARNING: HEAD did not change after commit (nothing to commit?)"
fi

if [[ "$POST_TREE_HASH" == "$PRE_TREE_HASH" && "$POST_COMMIT_SHA" != "$PRE_COMMIT_SHA" ]]; then
  echo "WARNING: commit created but tree hash unchanged — possible empty commit"
fi

echo "Post-commit state: SHA=$POST_COMMIT_SHA TREE=$POST_TREE_HASH"

# ─── Step 8: Sync to Milhy-PC ───────────────────────────────────────────────
echo "Syncing repository to Milhy-PC: $MILHY_PC_HOST:$MILHY_PC_REPO"
if ! rsync -a --delete \
  --exclude '.venv/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  "$ROOT/" "$MILHY_PC_HOST:$MILHY_PC_REPO/"; then
  echo "FATAL: rsync to Milhy-PC failed — commit exists locally but mirror is stale" >&2
  exit 1
fi

# Verify remote mirror SHA matches
REMOTE_SHA="$(ssh "$MILHY_PC_HOST" "cd '$MILHY_PC_REPO' && git rev-parse HEAD 2>/dev/null" || echo unknown)"
if [[ "$REMOTE_SHA" != "$POST_COMMIT_SHA" ]]; then
  echo "FATAL: Milhy-PC mirror SHA mismatch (expected $POST_COMMIT_SHA, got $REMOTE_SHA)" >&2
  exit 1
fi
echo "Milhy-PC mirror verified: $REMOTE_SHA"

# ─── Step 9: Trigger Milhy-PC CI gateway ────────────────────────────────────
echo "Triggering Milhy-PC CI gateway on $MILHY_PC_HOST:$MILHY_PC_REPO"
# shellcheck disable=SC2029 # Intentional client-side expansion of configured host/path/branch.
if ! ssh "$MILHY_PC_HOST" "cd '$MILHY_PC_REPO' && BRANCH='$TARGET_BRANCH' SOURCE_REMOTE=local tools/ci-agent.sh"; then
  echo "FATAL: Milhy-PC CI agent failed — commit exists locally but GitHub push may not have happened" >&2
  exit 1
fi

# ─── Step 10: Write atomic receipt ───────────────────────────────────────────
# The receipt is the ONLY proof of a successful pipeline run.
# If any step above failed, we never reach this point.
RECEIPT_FILE="$RECEIPT_DIR/${POST_COMMIT_SHA}-$(date +%Y%m%d-%H%M%S).json"
cat > "$RECEIPT_FILE" <<RECEIPT
{
  "status": "done",
  "commit_sha": "$POST_COMMIT_SHA",
  "tree_hash": "$POST_TREE_HASH",
  "pre_commit_sha": "$PRE_COMMIT_SHA",
  "pre_tree_hash": "$PRE_TREE_HASH",
  "diff_hash": "$PRE_DIFF_HASH",
  "message": $(printf '%s' "$MSG" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'),
  "host": "$(hostname)",
  "branch": "$TARGET_BRANCH",
  "timestamp": "$(date -Is)",
  "ci_report": "$(ls -1t conductor/ci/reports/${POST_COMMIT_SHA}-*.md 2>/dev/null | head -1 || echo unknown)",
  "safety_snapshot": "$SNAP"
}
RECEIPT

echo ""
echo "=== RECEIPT ==="
cat "$RECEIPT_FILE"
echo ""
echo "=== PIPELINE COMPLETE ==="
echo "Receipt: $RECEIPT_FILE"
echo "Commit:  $POST_COMMIT_SHA"
echo "Message: $MSG"
echo ""
echo "The agent MUST NOT claim 'done' without this receipt file."

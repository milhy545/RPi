#!/usr/bin/env bash
# finish-track.sh — safe local finish/commit handoff to Milhy-PC CI gateway.
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

usage() {
  cat <<'USAGE'
Usage: tools/finish-track.sh "commit message"

Runs local CI, creates a safety stash snapshot if needed, commits current changes,
syncs the repository to Milhy-PC, and triggers the Milhy-PC CI gateway. It does not push directly to GitHub.

Environment:
  MILHY_PC_HOST     SSH host for Milhy-PC (default: Milhy-PC)
  MILHY_PC_REPO     Repo path on Milhy-PC (default: /home/milhy777/Develop/RPi)
  TARGET_BRANCH     Branch to validate/push (default: master)
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then usage; exit 0; fi
if [[ $# -lt 1 ]]; then usage >&2; exit 2; fi

MSG="$1"
MILHY_PC_HOST="${MILHY_PC_HOST:-Milhy-PC}"
MILHY_PC_REPO="${MILHY_PC_REPO:-/home/milhy777/Develop/RPi}"
TARGET_BRANCH="${TARGET_BRANCH:-master}"

if [[ -z "$(git status --porcelain)" ]]; then
  echo "No changes to commit."
  exit 0
fi

SNAP="pre-finish-track-$(date +%Y%m%d-%H%M%S)"
echo "Creating safety stash snapshot: $SNAP"
git stash push -u -m "$SNAP" >/dev/null
# Re-apply immediately; stash remains as recoverable checkpoint.
git stash apply --index 'stash@{0}' >/dev/null || git stash apply 'stash@{0}' >/dev/null

echo "Running local CI..."
tools/run-ci.sh

echo "Committing..."
git add -A
git commit -m "$MSG"

echo "Syncing repository to Milhy-PC: $MILHY_PC_HOST:$MILHY_PC_REPO"
rsync -a --delete \
  --exclude '.venv/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  "$ROOT/" "$MILHY_PC_HOST:$MILHY_PC_REPO/"

echo "Triggering Milhy-PC CI gateway on $MILHY_PC_HOST:$MILHY_PC_REPO"
# shellcheck disable=SC2029 # Intentional client-side expansion of configured host/path/branch.
ssh "$MILHY_PC_HOST" "cd '$MILHY_PC_REPO' && BRANCH='$TARGET_BRANCH' SOURCE_REMOTE=local tools/ci-agent.sh"

echo "Done. Milhy-PC CI agent validates and pushes to GitHub only on success."

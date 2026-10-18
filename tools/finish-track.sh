#!/usr/bin/env bash
# Bezpečný pomocný skript pro commit; CI musí uspět před vytvořením commitu.
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ $# -ne 1 || -z "${1//[[:space:]]/}" ]]; then
  echo "Usage: tools/finish-track.sh \"commit message\"" >&2
  exit 2
fi
MESSAGE="$1"

HOSTNAME_LOWER="$(hostname 2>/dev/null | tr '[:upper:]' '[:lower:]' || echo unknown)"
IS_RPI=0
if [[ "$HOSTNAME_LOWER" == *"rpi"* || "$ROOT" == *"/rpi-dashboard"* ]]; then
  IS_RPI=1
fi

if ! BRANCH="$(git symbolic-ref --quiet --short HEAD 2>/dev/null)" || [[ -z "$BRANCH" ]]; then
  echo "FATAL: finish-track requires a named branch." >&2
  exit 1
fi
if [[ "$BRANCH" == "main" && $IS_RPI -ne 1 ]]; then
  echo "FATAL: finish-track will not create commits directly on main." >&2
  exit 1
fi
if [[ -z "$(git status --porcelain)" ]]; then
  echo "FATAL: there are no changes to commit." >&2
  exit 1
fi

if [[ -n "${CI_PROFILE:-}" ]]; then
  PROFILE="$CI_PROFILE"
elif [[ "$HOSTNAME_LOWER" == *"rpi"* || "$ROOT" == *"/rpi-dashboard"* ]]; then
  PROFILE="rpi-focused"
else
  PROFILE="milhy-full"
fi
case "$PROFILE" in
  rpi-focused|rpi-candidate|milhy-full|github-safe) ;;
  *)
    echo "FATAL: unsupported CI profile '$PROFILE'; refusing to snapshot or commit changes." >&2
    exit 2
    ;;
esac

# Uchovej index, sledovane zmeny i untracked soubory jako obnovitelny snapshot.
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
if ! git stash push --include-untracked -m "pre-finish-track-$STAMP"; then
  echo "FATAL: safety snapshot could not be created." >&2
  exit 1
fi
SNAPSHOT="$(git rev-parse --verify 'stash@{0}')"
if ! git stash apply --index "$SNAPSHOT"; then
  echo "FATAL: safety snapshot exists at $SNAPSHOT but could not be restored." >&2
  echo "Resolve the worktree manually; do not discard the snapshot." >&2
  exit 1
fi
echo "Safety snapshot retained: $SNAPSHOT"

echo "Running CI profile '$PROFILE' before commit creation."
if ! tools/run-ci.sh --profile "$PROFILE"; then
  echo "FATAL: CI failed; no commit was created. Changes and safety snapshot are retained." >&2
  exit 1
fi

git add -A
if ! python3 - <<'PY'
import subprocess
import sys

raw = subprocess.check_output(["git", "diff", "--cached", "--name-only", "-z"])
paths = [item.decode("utf-8", "surrogateescape") for item in raw.split(b"\0") if item]
forbidden = (
    "conductor/ci/reports/",
    "conductor/ci/receipts/",
    "tests/e2e/results/",
)
bad = [
    path for path in paths
    if path.startswith(forbidden)
    or ".forensics" in path.split("/")
    or "__pycache__" in path.split("/")
    or ".venv" in path.split("/")
    or path.endswith(".pyc")
    or path.rsplit("/", 1)[-1] in {"playback-memory.json", "yt-cookies.txt"}
]
if bad:
    print("FATAL: refusing runtime artifacts in the commit:", file=sys.stderr)
    print("\n".join(bad), file=sys.stderr)
    sys.exit(1)
PY
then
  echo "FATAL: staged runtime artifacts were found; nothing was committed." >&2
  exit 1
fi

git diff --cached --check
if git diff --cached --quiet; then
  echo "FATAL: CI passed, but there are no staged changes to commit." >&2
  exit 1
fi

git commit -m "$MESSAGE"
COMMIT_SHA="$(git rev-parse HEAD)"
TREE_SHA="$(git rev-parse 'HEAD^{tree}')"
echo "COMMIT_SHA=$COMMIT_SHA"
echo "TREE_SHA=$TREE_SHA"
echo "PR CI and an exact-main GitHub Actions receipt are still required before claiming completion."

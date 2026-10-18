#!/usr/bin/env bash
# Spustí GitHub-hosted CI bez externích Actions.
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3.12}"
UV_VERSION="${UV_VERSION:-0.13.1}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: required Python interpreter '$PYTHON_BIN' is unavailable." >&2
  exit 1
fi

PYTHON_PATH="$(command -v "$PYTHON_BIN")"
if ! "$PYTHON_PATH" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)'; then
  echo "ERROR: GitHub CI requires Python 3.12; found $($PYTHON_PATH --version 2>&1)." >&2
  exit 1
fi

TEMP_ROOT="${RUNNER_TEMP:-${TMPDIR:-/tmp}}"
UV_ENV="$TEMP_ROOT/rpi-dashboard-uv-${GITHUB_RUN_ID:-local}"
PYTHON_SHIMS="$TEMP_ROOT/rpi-dashboard-python-${GITHUB_RUN_ID:-local}"
mkdir -p "$TEMP_ROOT" "$PYTHON_SHIMS"
"$PYTHON_PATH" -m venv "$UV_ENV"
"$UV_ENV/bin/python" -m pip install --disable-pip-version-check "uv==$UV_VERSION"
ln -sfn "$PYTHON_PATH" "$PYTHON_SHIMS/python3"

export PATH="$PYTHON_SHIMS:$UV_ENV/bin:$PATH"
export UV_CMD="$UV_ENV/bin/uv"
export CI_PROFILE="${CI_PROFILE:-github-safe}"

"$UV_CMD" sync --locked --extra dev --python "$PYTHON_PATH"
if tools/run-ci.sh; then
  :
else
  ci_status=$?
  short_sha="$(git rev-parse --short HEAD)"
  reports=("conductor/ci/reports/${short_sha}-"*.md)
  if [[ -f "${reports[-1]}" ]]; then
    echo "CI failed; printing captured report ${reports[-1]}:"
    cat "${reports[-1]}"
  else
    echo "CI failed with status $ci_status and produced no report under conductor/ci/reports/." >&2
  fi
  exit "$ci_status"
fi
python3 scripts/create_receipt.py
tools/verify-done.sh

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  {
    echo "## RPi Dashboard CI"
    echo
    echo "- Commit: $(git rev-parse HEAD)"
    echo "- Profile: $CI_PROFILE"
    echo "- Receipt validation: passed"
  } >> "$GITHUB_STEP_SUMMARY"
fi

#!/usr/bin/env bash
# run-ci.sh — local/Milhy-PC/GitHub-safe CI for RPi Dashboard.
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

REPORT_DIR="${REPORT_DIR:-conductor/ci/reports}"
mkdir -p "$REPORT_DIR"
SHA="$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d-%H%M%S)"
REPORT="$REPORT_DIR/${SHA}-$(date +%Y%m%d-%H%M%S).md"
STRICT_SECURITY_TOOLS="${STRICT_SECURITY_TOOLS:-0}"
FAILURES=0

log() { printf '%s\n' "$*"; }
append() { printf '%s\n' "$*" >> "$REPORT"; }

run_step() {
  local name="$1"; shift
  log "==> $name"
  append "## $name"
  append '```text'
  set +e
  "$@" >> "$REPORT" 2>&1
  local rc=$?
  set -e
  append '```'
  append "Result: $rc"
  append ""
  if [[ $rc -ne 0 ]]; then
    log "FAIL: $name ($rc)"
    FAILURES=$((FAILURES + 1))
  else
    log "PASS: $name"
  fi
}

optional_step() {
  local tool="$1"; shift
  local name="$1"; shift
  if command -v "$tool" >/dev/null 2>&1; then
    run_step "$name" "$@"
  else
    append "## $name"
    append "SKIP: required tool '$tool' is not installed."
    append ""
    log "SKIP: $name ($tool missing)"
    if [[ "$STRICT_SECURITY_TOOLS" == "1" ]]; then
      FAILURES=$((FAILURES + 1))
    fi
  fi
}

{
  echo "# RPi Dashboard CI Report"
  echo ""
  echo "- Commit: $(git rev-parse HEAD 2>/dev/null || echo unknown)"
  echo "- Host: $(hostname)"
  echo "- Time: $(date -Is)"
  echo ""
} > "$REPORT"

run_step "git diff whitespace check" git diff --check
run_step "Python compile: webserver" python3 -m py_compile webserver.py
run_step "Python compile: tui" python3 -m py_compile tui.py
run_step "Python compile: mode_switcher" python3 -m py_compile mode_switcher.py
run_step "Python compile: keys2mpv" python3 -m py_compile keys2mpv.py
python3 tools/extract-webui-js.py webserver.py > /tmp/rpi-webui-ci.js
run_step "Extract WebUI JS" test -s /tmp/rpi-webui-ci.js

if command -v node >/dev/null 2>&1; then
  run_step "Node syntax check: embedded WebUI JS" node --check /tmp/rpi-webui-ci.js
else
  log "SKIP: Node syntax check (node missing)"
  append "## Node syntax check: embedded WebUI JS"
  append "SKIP: node is not installed."
  append ""
fi

if [[ -f test_testaudio_webui.py ]]; then
  # Configurable WebUI port (default 8080) and URL for safe audio tests
  WEBUI_PORT="${RPIDASHBOARD_WEBUI_PORT:-8080}"
  export RPIDASHBOARD_WEBUI_URL="http://127.0.0.1:${WEBUI_PORT}"
  if curl -fsS --max-time 2 "${RPIDASHBOARD_WEBUI_URL}/" >/dev/null 2>&1; then
    run_step "Safe WebUI audio unit tests" python3 test_testaudio_webui.py
  else
    log "SKIP: Safe WebUI audio unit tests (server not running on ${RPIDASHBOARD_WEBUI_URL})"
    append "## Safe WebUI audio unit tests"
    append "SKIP: WebUI server is not running on ${RPIDASHBOARD_WEBUI_URL}."
    append ""
  fi
fi

if [[ -f test_audio_mutating_webui.py ]]; then
  # This file is syntax-checked only by default because it can mutate live audio.
  run_step "Python compile: mutating audio test" python3 -m py_compile test_audio_mutating_webui.py
fi
if [[ -f test_production_api.py ]]; then
  run_step "Python compile: production API test" python3 -m py_compile test_production_api.py
fi

optional_step shellcheck "ShellCheck shell scripts" bash -lc 'shopt -s nullglob; shellcheck *.sh provisioning/*.sh tools/*.sh'
optional_step gitleaks "Gitleaks secret scan" gitleaks detect --no-git --redact --source .
optional_step bandit "Bandit Python security scan (high severity gate)" bandit -q -lll -r . -x .venv,__pycache__
optional_step pip-audit "pip-audit dependency scan" pip-audit
# Run full pytest suite to ensure comprehensive test coverage
run_step "Run full pytest suite" uv run pytest -q

run_step "Forbidden regression strings" bash -lc '! grep -nE "GFN-TV|killall mpv|pkill mpv" webserver.py tui.py mode_switcher.py keys2mpv.py 2>/dev/null'

append "# Final Result"
if [[ $FAILURES -eq 0 ]]; then
  append "PASS"
  log "CI PASS: $REPORT"
  exit 0
fi
append "FAILURES: $FAILURES"
log "CI FAIL ($FAILURES): $REPORT"
exit 1

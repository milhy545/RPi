#!/usr/bin/env bash
# run-ci.sh — Profile-aware, safe CI for RPi Dashboard across RPi and Milhy-PC.
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH=".:${PYTHONPATH:-}"

# Determine host identity
HOSTNAME_LOWER="$(hostname 2>/dev/null | tr '[:upper:]' '[:lower:]' || echo "unknown")"
IS_RPI=0
if [[ "$HOSTNAME_LOWER" == *"rpi"* || "$ROOT" == *"/rpi-dashboard"* ]]; then
  IS_RPI=1
fi

# Determine default profile based on host unless explicitly set
DEFAULT_PROFILE="milhy-full"
if [[ $IS_RPI -eq 1 ]]; then
  DEFAULT_PROFILE="rpi-focused"
fi

PROFILE="${CI_PROFILE:-$DEFAULT_PROFILE}"

# Parse command line flags
while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      PROFILE="$2"
      shift 2
      ;;
    --profile=*)
      PROFILE="${1#*=}"
      shift 1
      ;;
    *)
      shift 1
      ;;
  esac
done

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
  echo "- Profile: $PROFILE"
  echo "- Time: $(date -Is)"
  echo ""
} > "$REPORT"

log "Executing CI profile: $PROFILE on host $(hostname)"

# Step: Git diff whitespace check
run_step "git diff whitespace check" git diff --check

# Step: Python syntax compilation
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
  run_step "Python compile: mutating audio test" python3 -m py_compile test_audio_mutating_webui.py
fi
if [[ -f test_production_api.py ]]; then
  run_step "Python compile: production API test" python3 -m py_compile test_production_api.py
fi

# Profile specific executions
case "$PROFILE" in
  rpi-focused)
    log "Profile 'rpi-focused': Running bounded focused safe tests for RPi."
    append "## Execution Profile: rpi-focused"

    # Run focused RPi-safe tests (bounded, no browser/heavy suite)
    if [[ -f "$HOME/.local/bin/uv" ]]; then
      run_step "Run focused RPi safe CI tests" "$HOME/.local/bin/uv" run --extra dev pytest tests/test_rpi_safe_ci_pipeline.py -q
    elif command -v uv >/dev/null 2>&1; then
      run_step "Run focused RPi safe CI tests" uv run --extra dev pytest tests/test_rpi_safe_ci_pipeline.py -q
    elif [[ -x .venv/bin/pytest ]]; then
      run_step "Run focused RPi safe CI tests" .venv/bin/pytest tests/test_rpi_safe_ci_pipeline.py -q
    else
      run_step "Run focused RPi safe CI tests" python3 -m pytest tests/test_rpi_safe_ci_pipeline.py -q
    fi

    append "Lightweight RPi bounded tests completed. Full pytest suite deferred to Milhy-PC."
    append ""
    ;;

  milhy-full|github-safe)
    # Extended static analysis and security tools on Milhy-PC
    if [[ "${EXTENDED_CI:-1}" == "1" ]]; then
      optional_step shellcheck "ShellCheck shell scripts" bash -lc 'shopt -s nullglob; shellcheck *.sh provisioning/*.sh tools/*.sh'
      optional_step gitleaks "Gitleaks secret scan" gitleaks detect --no-git --redact --source . -c .gitleaks.toml
      _BANDIT="${BANDIT_CMD:-$(ls .venv/bin/bandit 2>/dev/null || command -v bandit 2>/dev/null || true)}"
      _PIP_AUDIT="${PIP_AUDIT_CMD:-$(ls .venv/bin/pip-audit 2>/dev/null || command -v pip-audit 2>/dev/null || true)}"

      if [[ -n "$_BANDIT" && -x "$_BANDIT" ]]; then
        run_step "Bandit Python security scan (high severity gate)" "$_BANDIT" -q -lll -r . -x ./.venv,./__pycache__,./tests
      else
        append "## Bandit Python security scan (high severity gate)"
        append "SKIP: bandit not found."
        append ""
      fi

      if [[ -n "$_PIP_AUDIT" && -x "$_PIP_AUDIT" ]]; then
        run_step "pip-audit dependency scan" "$_PIP_AUDIT" --skip-editable
      else
        append "## pip-audit dependency scan"
        append "SKIP: pip-audit not found."
        append ""
      fi
    fi

    # Code quality gates: Ruff & Mypy
    _RUFF="$(command -v ruff || ls .venv/bin/ruff 2>/dev/null || true)"
    if [[ -n "$_RUFF" && -x "$_RUFF" ]]; then
      run_step "Ruff linter check" "$_RUFF" check .
    fi

    _MYPY="$(command -v mypy || ls .venv/bin/mypy 2>/dev/null || true)"
    if [[ -n "$_MYPY" && -x "$_MYPY" ]]; then
      run_step "Mypy type checker" "$_MYPY" --explicit-package-bases .
    fi

    # Full pytest suite execution on Milhy-PC
    if [[ -f "$HOME/.local/bin/uv" ]]; then
      run_step "Run full pytest suite" "$HOME/.local/bin/uv" run --extra dev pytest -q
    elif command -v uv >/dev/null 2>&1; then
      run_step "Run full pytest suite" uv run --extra dev pytest -q
    elif [[ -x .venv/bin/pytest ]]; then
      run_step "Run full pytest suite" .venv/bin/pytest -q
    elif command -v pytest >/dev/null 2>&1; then
      run_step "Run full pytest suite" pytest -q
    else
      run_step "Run full pytest suite" python3 -m pytest -q
    fi

    # Emit milhy-full receipt if all tests pass
    if [[ $FAILURES -eq 0 ]]; then
      CURRENT_SHA="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
      CURRENT_TREE="$(git write-tree 2>/dev/null || echo unknown)"
      RECEIPT_DIR="conductor/ci/receipts"
      RECEIPT_FILE="$RECEIPT_DIR/${CURRENT_SHA}-receipt.json"
      mkdir -p "$RECEIPT_DIR"
      python3 -c "
import json, datetime
receipt = {
  'commit_sha': '$CURRENT_SHA',
  'tree_hash': '$CURRENT_TREE',
  'profile': 'milhy-full',
  'host': '$(hostname)',
  'status': 'done',
  'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'ci_report': '$REPORT',
  'actions_url': '',
  'evidence': {'e2e': 'pending', 'rpi_gate': {'status': 'N/A'}}
}
with open('$RECEIPT_FILE', 'w') as f:
  json.dump(receipt, f, indent=2)
print('Emitted milhy-full receipt: $RECEIPT_FILE')
" 2>/dev/null || echo "WARN: Failed to emit receipt"
    fi

    # Remote Playwright E2E on Milhy-PC (required for milhy-full profile)
    # Only run if this is milhy-full (not github-safe which is cloud/hardware-safe)
    CURRENT_SHA="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
    if [[ "$PROFILE" == "milhy-full" ]]; then
      if command -v npm >/dev/null 2>&1 && [[ -d "tests/e2e" ]]; then
        # Preserve raw Playwright exit status - FAIL the step if E2E fails
        # TARGET_URL must be set to staged RPi candidate for remote validation
        if [[ -z "${TARGET_URL:-}" ]]; then
          run_step "Remote Playwright E2E (Milhy-PC)" bash -c "echo 'ERROR: TARGET_URL not set for E2E. Set to staged candidate URL.' && exit 1"
        else
          if run_step "Remote Playwright E2E (Milhy-PC)" bash -c "cd tests/e2e && TARGET_URL='${TARGET_URL}' npm test"; then
            # Emit SHA-bound E2E manifest on success
            E2E_MANIFEST_DIR="tests/e2e/results"
            mkdir -p "$E2E_MANIFEST_DIR"
            CURRENT_TREE="$(git write-tree 2>/dev/null || echo unknown)"
            python3 -c "
import json, datetime
manifest = {
  'sha': '$CURRENT_SHA',
  'tree_hash': '$CURRENT_TREE',
  'status': 'done',
  'profile': 'milhy-full',
  'host': '$(hostname)',
  'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'target_url': '${TARGET_URL}'
}
with open('$E2E_MANIFEST_DIR/e2e-manifest-$CURRENT_SHA.json', 'w') as f:
  json.dump(manifest, f, indent=2)
with open('$E2E_MANIFEST_DIR/$CURRENT_SHA.json', 'w') as f:
  json.dump(manifest, f, indent=2)
" 2>/dev/null
          fi
        fi
      else
        # FAIL: Playwright/E2E is required for milhy-full, missing means failure
        run_step "Remote Playwright E2E (Milhy-PC)" bash -c "echo 'FAIL: Playwright or E2E suite not available. Required for milhy-full profile.' && exit 1"
      fi
    fi
    ;;

  rpi-candidate)
    log "Profile 'rpi-candidate': Verifying safe candidate hardware smoke on RPi."
    append "## Execution Profile: rpi-candidate"

    # Ban browser execution on RPi
    if pgrep -f "chromium" >/dev/null 2>&1 || pgrep -f "chrome" >/dev/null 2>&1 || pgrep -f "firefox" >/dev/null 2>&1 || pgrep -f "playwright" >/dev/null 2>&1; then
      run_step "RPi Browser Ban Enforcement" bash -c "echo 'ERROR: Browser processes detected on RPi!' && exit 1"
    else
      run_step "RPi Browser Ban Enforcement" true
    fi

    # Check RPi Guard status with sustained CPU sampling
    run_step "RPi Hardware & Playback Guard Check" python3 -c "from rpi_dashboard.ci.rpi_guard import RPiGuard; g = RPiGuard(); st = g.check_status(sustained_cpu_samples=3); print('RPi Status:', st); exit(1 if st['busy'] else 0)"

    # Execute focused safe tests on RPi candidate
    if [[ -f "$HOME/.local/bin/uv" ]]; then
      run_step "Run focused RPi safe CI tests" "$HOME/.local/bin/uv" run --extra dev pytest tests/test_rpi_safe_ci_pipeline.py -v
    elif command -v uv >/dev/null 2>&1; then
      run_step "Run focused RPi safe CI tests" uv run --extra dev pytest tests/test_rpi_safe_ci_pipeline.py -v
    elif [[ -x .venv/bin/pytest ]]; then
      run_step "Run focused RPi safe CI tests" env PYTHONPATH=".:${PYTHONPATH:-}" .venv/bin/pytest tests/test_rpi_safe_ci_pipeline.py -v
    else
      run_step "Run focused RPi safe CI tests" env PYTHONPATH=".:${PYTHONPATH:-}" python3 -m pytest tests/test_rpi_safe_ci_pipeline.py -v
    fi

    # Emit atomic exact-SHA RPi candidate evidence receipt if all tests pass
    if [[ $FAILURES -eq 0 ]]; then
      CURRENT_SHA="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
      CURRENT_TREE="$(git write-tree 2>/dev/null || echo unknown)"
      RECEIPT_DIR="conductor/ci/receipts"
      RECEIPT_FILE="$RECEIPT_DIR/${CURRENT_SHA}-receipt.json"
      mkdir -p "$RECEIPT_DIR"
      python3 -c "
import json, datetime
receipt = {
  'commit_sha': '$CURRENT_SHA',
  'tree_hash': '$CURRENT_TREE',
  'profile': 'rpi-candidate',
  'host': '$(hostname)',
  'status': 'done',
  'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'ci_report': '$REPORT',
  'actions_url': '',
  'evidence': {'rpi_gate': {'status': 'PASS', 'busy': False}}
}
with open('$RECEIPT_FILE', 'w') as f:
  json.dump(receipt, f, indent=2)
print('Emitted RPi candidate receipt: $RECEIPT_FILE')
" 2>/dev/null || echo "WARN: Failed to emit RPi receipt"
    fi
    ;;

  *)
    log "WARNING: Unknown profile '$PROFILE'. Falling back to default checks."
    append "## Unknown Profile: $PROFILE"
    ;;
esac

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

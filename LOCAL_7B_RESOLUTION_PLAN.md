# Local 7B Model Resolution Plan — Milhy-PC (kilo desktop)

This plan covers everything that **cannot** be resolved in the cloud sandbox
(`/workspace/rpi`) and must be executed on the local Milhy-PC host running the
kilo desktop 7B model. It is organized by track, with exact commands and
acceptance criteria.

---

## 1. Why these items cannot be resolved in the cloud

| Missing capability | Cloud status | Impact |
|---|---|---|
| `python3` / `uv` / `.venv` | Not installed | Cannot run pytest, ruff, mypy, pip-audit, bandit |
| `gitleaks` | Not installed | Cannot run secret scanning |
| `gh` authentication | `GH_TOKEN` invalid | Cannot access GitHub PRs, security alerts, or push |
| RPi hardware (Pi 3B, 731 MB RAM) | Not accessible | Cannot run HW-ONLY tasks, 24h soak, Playwright on Pi |
| Ephemeral sandbox | Files won't persist | All changes must be pushed via Milhy-PC gateway |

---

## 2. Already resolved in the cloud (no local action needed)

- **PR backlog** (`conductor/tracks/github-pr-backlog_20261018/plan.md`): All 48 PRs
  dispositioned, all checkboxes `[x]`. Only remaining item is the non-mutating
  RPi candidate smoke (HW-ONLY, see Section 5).
- **report-processor.service**: Removed `User=milhy777` (was causing 216/GROUP
  failures on every 1-minute tick), added `flock -n` overlap prevention,
  documented preference for `systemd/user/report-processor.service`.
- **report-processor.timer**: `AccuracySec` raised `1s` → `1min`,
  `RandomizedDelaySec=30s` added to reduce timer pressure.
- **AGENTS.md**: Rewritten with only high-signal, repo-specific guidance.

---

## 3. Security scanning — local Milhy-PC (priority: high)

### 3.1 Prerequisites on Milhy-PC
```bash
# Ensure kilo desktop 7B model has access to the repo
cd /home/milhy777/Develop/RPi

# Install project dependencies (locked)
uv sync --extra dev

# Install security tools if not in dev extra
uv pip install gitleaks bandit pip-audit shellcheck  # or via system package manager
```

### 3.2 gitleaks secret scan
```bash
gitleaks detect --no-git --redact --source . -c .gitleaks.toml
```
- **Expectation**: No findings outside allowlisted paths (`.venv`,
  `conductor/ci/reports`).
- **If findings**: Review each, either remove the secret or add to
  `.gitleaks.toml` allowlist with justification. Never commit secrets.
- **Forbidden strings gate**: `GFN-TV`, `killall mpv`, `pkill mpv` must not
  appear in `webserver.py`, `tui.py`, `mode_switcher.py`, `keys2mpv.py`.

### 3.3 pip-audit dependency scan
```bash
uv run --locked --extra dev pip-audit --skip-editable
```
- **Expectation**: No known vulnerabilities in locked dependency set.
- `pyproject.toml` dev extra already pins `aiohttp>=3.14.4`,
  `certifi>=2026.10.19`, `pip>=26.2.2` (resolved by PR #117).

### 3.4 Bandit Python security scan
```bash
uv run --locked --extra dev bandit -q -lll -r . -x ./.venv,./__pycache__,./tests
```
- **Expectation**: Exit 0, no HIGH-severity findings.

### 3.5 ShellCheck
```bash
shellcheck *.sh provisioning/*.sh tools/*.sh
```
- **Expectation**: Exit 0.

### 3.6 GitHub CodeQL
- The repository uses local-only Actions; CodeQL default setup was enabled for
  Actions, JavaScript/TypeScript, and Python per the PR backlog plan.
- On Milhy-PC, verify CodeQL analysis passes on the exact PR revision before
  merging any PR.

---

## 4. Verification-Coverage-Hardening Phase 1 (DEV, can run on Milhy-PC without hardware)

### 4.1 Run the full local test suite
```bash
cd /home/milhy777/Develop/RPi
uv sync --extra dev
uv run python -m pytest -q
```
- **Baseline**: 312+ tests passing (from plan.md).
- **Target**: All tests pass.

### 4.2 Transport disconnect tests (already implemented)
```bash
uv run python -m pytest tests/test_transport_disconnect.py -v
```
- **Already passing**: `test_transport_disconnect.py` covers
  `BrokenPipeError`/`ConnectionResetError` in `_write_body()`.

### 4.3 Shutdown behavior tests (already covered in test_mode_switcher.py)
```bash
uv run python -m pytest tests/test_mode_switcher.py -v
```
- Covers `_teardown_active_process`, SIGTERM/SIGINT handling,
  `_teardown_and_exit`, watchdog timeout/cancellation.
- **No new file needed**: `test_shutdown_behavior.py` referenced in plan.md
  is superseded by existing `test_mode_switcher.py` coverage.

### 4.4 Coverage gate (>80%)
```bash
uv run python -m pytest --cov=rpi_dashboard --cov-fail-under=80 -q
```
- **Current baseline**: 60.11% (measured 2026-08-02).
- **Target**: >80% meaningful coverage.
- If below target, add behavior-focused tests in `tests/` (no no-op
  assertions). Focus on: CEC, terminal, route, EOF, service-unit, audio,
  network, negative-path tests.

### 4.5 Lint and typecheck
```bash
uv run ruff check .        # selects only F, ignores F841
uv run mypy .              # Python 3.12
```

### 4.6 report-processor fix verification (local)
After applying the cloud systemd edits on the RPi:
```bash
# On the RPi host (not Milhy-PC)
systemctl --user daemon-reload
systemctl --user restart report-processor.timer
systemctl --user status report-processor.service
journalctl --user -u report-processor.service -n 20
```
- **Expectation**: No 216/GROUP failures, no repeated every-minute log storm.

---

## 5. Verification-Coverage-Hardening Phases 2-5 (HW-ONLY — requires live RPi)

These require physical access to the Raspberry Pi 3 Model B and must be run
from Milhy-PC via SSH or the self-hosted RPi GitHub runner.

| Phase | Task | Command / Evidence |
|---|---|---|
| 2 | Baseline metrics | Record per-process/per-core CPU, RSS/PSS, swap, wakeups → `baseline_20260727/performance_metrics.json` |
| 3 | tmux-restore.service | `journalctl -u tmux-restore.service -n 50`; fix or retire with tested replacement |
| 3 | USB device 5 FIQ | Correlate `dmesg` FIQ NYET/timeout with PipeWire xruns |
| 3 | PipeWire tuning | Measure xrun/latency per route; tune buffers/quantum/resampling |
| 3 | triggerhappy | Fix `th-cmd` hook failures for Xbox/input event nodes |
| 3 | Wi-Fi scan | `brcmfmac` scan failure → bounded retry + visible health |
| 3 | Tailscale/DNS | Classify remote outage; bounded health/recovery display |
| 3 | Logrotate regression | Verify `/tmp/tui_fresh.log` rotation is safe |
| 4 | TUI profiling | Profile `tui.py` memory/timers/subprocesses; target ~20 MiB RSS |
| 4 | Optimization results | Document before/after in `baseline_20260727/optimization_results.md` |
| 5 | Playwright baselines | Remote from Milhy-PC: desktop, tablet, mobile viewports |
| 5 | 24-hour soak | `tools/soak_test.py --duration 24h`; zero unexplained log ledger items |

**Acceptance criteria**:
- `systemctl --failed` and `systemctl --user --failed` contain no unresolved project-owned unit
- Dashboard stop, WebUI disconnect, tmux restore, logrotate, Wi-Fi/Tailscale, triggerhappy, USB transport, audio xrun regression checks pass
- `pytest --cov=rpi_dashboard` > 80%
- `tools/verify-done.sh` exits 0

---

## 6. PR backlog remaining item — RPi candidate smoke (HW-ONLY)

From `conductor/tracks/github-pr-backlog_20261018/plan.md` line 38:
> Run the non-mutating RPi candidate smoke for runtime-related changes after
> confirming the current RPi host mapping; the live SSH alias and stored device
> map disagree, so no hardware candidate has been staged.

### Steps on Milhy-PC:
1. Confirm RPi host mapping (SSH alias vs stored device map disagree — resolve
   which is correct).
2. Stage candidate code in isolated worktree:
   `/home/milhy777/rpi-dashboard-candidate-<sha>`
3. Run `tools/run-ci.sh --profile rpi-candidate` on RPi
   - **Guard**: Never disrupt active playback (`mpv`, `steamlink`, `moonlight`)
   - **Guard**: Browsers/Playwright strictly forbidden on RPi
   - **Guard**: If user playback starts mid-run, abort immediately and requeue
4. On success, the RPi candidate receipt is emitted:
   `conductor/ci/receipts/{sha}-receipt.json`

---

## 7. CI pipeline and finish-track / verify-done (Milhy-PC gateway)

### 7.1 Run CI profiles
```bash
# On Milhy-PC (full suite)
tools/run-ci.sh --profile milhy-full

# On RPi (lightweight, no browsers)
tools/run-ci.sh --profile rpi-focused

# GitHub-safe (static + unit, no hardware gates)
tools/run-ci.sh --profile github-safe
```

### 7.2 Commit via finish-track (NEVER `git commit` directly)
```bash
tools/finish-track.sh "feat: descriptive commit message"
```
- Creates safety stash snapshot (`pre-finish-track-{timestamp}`)
- Runs selected CI profile before staging
- Blocks runtime artifacts: `*.pyc`, `__pycache__/`, `.venv/`,
  `.forensics/`, `playback-memory.json`, `yt-cookies.txt`,
  `conductor/ci/reports/`, `conductor/ci/receipts/`
- Creates new commit (never amends)
- Does NOT push

### 7.3 Push and merge (Milhy-PC only — RPi MUST NEVER push)
- Milhy-PC is the sole GitHub push/merge gateway.
- Push the candidate branch to GitHub from Milhy-PC.
- Wait for GitHub Actions push CI on `main` to create the exact-main receipt:
  `conductor/ci/receipts/{sha}-{timestamp}-github-main.json`

### 7.4 verify-done (exit 0 required before claiming done)
```bash
tools/verify-done.sh
```
Checks: git status clean, receipt for HEAD SHA/tree, Milhy-PC mirror matches,
HEAD pushed to origin, no runtime artifacts, no forbidden strings.

---

## 8. Execution order (recommended)

1. `uv sync --extra dev` on Milhy-PC
2. Security scans: gitleaks → pip-audit → bandit → shellcheck
3. `uv run ruff check .` and `uv run mypy .`
4. `uv run python -m pytest -q` and coverage gate
5. Fix any failures; add tests if coverage < 80%
6. `tools/run-ci.sh --profile github-safe`
7. `tools/finish-track.sh "<message>"`
8. Push from Milhy-PC to GitHub
9. Wait for GitHub Actions push CI receipt
10. `tools/verify-done.sh` (exit 0)
11. HW-ONLY phases (RPi candidate smoke, 24h soak) when hardware is available

---

## 9. Safety constraints (from conductor/ci/SAFETY-RULES.md)

- Never claim "done" unless `tools/verify-done.sh` exits 0.
- Never commit without CI passing via `tools/finish-track.sh`.
- RPi must never `git push`; Milhy-PC is the sole push/merge gateway.
- Never push runtime artifacts or forbidden strings (`GFN-TV`,
  `killall mpv`, `pkill mpv`).
- Candidate checks on RPi must never disrupt active playback.
- Browsers/Playwright strictly forbidden on RPi.

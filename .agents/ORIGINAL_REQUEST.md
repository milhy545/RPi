# Original User Request

## Initial Request — 2026-06-28T10:20:34Z

Perform a comprehensive System Overhaul of the RPi Dumb TV Dashboard — a Python/Textual TUI + aiohttp WebUI controller for a Raspberry Pi 3B+ (1 GB RAM) connected to a living room TV. The overhaul covers repo hygiene, critical bug fixes, code quality improvements, security hardening, and completion of three open feature tracks.

Working directory: /home/milhy777/rpi-dashboard
Integrity mode: development

## Context

**Tech stack:** Python 3.12 (managed via `uv`), Textual TUI (`tui.py`, ~1,070 lines), aiohttp web server (`webserver.py`, 2,729 lines / 182 KB), systemd services.
**Constraints:** RPi 3B+ with 1 GB RAM — TUI must stay ≤ 20 MB RSS. No heavy compilation. Temperature-aware.
**CI pipeline:** `tools/run-ci.sh` runs whitespace checks, Python compile, JS syntax, shellcheck, bandit, pytest, regression strings, and generates reports. `tools/verify-done.sh` validates completion (8 checks including receipt, mirror sync, no runtime artifacts). All commits go through `tools/finish-track.sh`.
**Current state:** `main` branch, 1 local commit ahead of origin (`0d52732`). 9 modified files + 1 untracked test file in working tree. The rename `webserver_8099.py` → `webserver.py` is already done.

### Key Metrics from Codebase Analysis

| Metric | Current State |
|--------|---------------|
| Bare `except:` remaining | **2** (keys2mpv.py lines 48, 65) |
| `except Exception:` with `pass` | **50+** in webserver.py (many swallow errors silently) |
| Resource leaks | **1 critical** (PA_DLNA_LOG open without context manager, webserver.py:879) |
| WebSocket auth (port 8098) | **NONE** — full tmux/shell access to anyone on network ⚠️ |
| WiFi password exposure | In `nmcli` cmdline args AND GET query params ⚠️ |
| Type hint coverage (webserver.py) | **~4%** (5 of 124+ functions) |
| Type hint coverage (tui.py) | **~45%** |
| Test files | 6 in tests/ + 5 legacy at project root |
| CORS | Hardcoded `localhost` only |
| Rate limiting | POST only, GET exempt |
| Legacy artifacts | `webserver-8099.service`, `webserver_8099.py.bak`, stale ref in `extract-webui-js.py` |
| Config duplication | `config.py` constants duplicated in `webserver.py` lines 26-31 |

## Requirements

### R1. Repository Cleanup & Hygiene
Clean up the Git repository: stash or commit the current 9 modified working tree files. Resolve merge conflicts in PR #20 and merge or close PRs #15 and #20. Delete all merged branches. Remove legacy files (`webserver-8099.service`, `webserver_8099.py.bak`). Fix the stale `webserver_8099.py` fallback path in `tools/extract-webui-js.py`. Eliminate config constant duplication between `config.py` and `webserver.py` (single source of truth in `config.py`). Ensure GitHub Actions CI passes on `main`.

### R2. Critical Safety Fixes
Fix the 2 remaining bare `except:` clauses in `keys2mpv.py` (lines 48, 65) — replace with appropriate specific exception types. Fix the resource leak in `webserver.py:879` where `PA_DLNA_LOG` is opened without a context manager. Review the 50+ `except Exception: pass` blocks in `webserver.py` — for each, either log the exception or handle it meaningfully (silent swallowing masks real failures). **Most critically:** add IP-allowlist authentication to the WebSocket terminal server on port 8098, which currently grants unauthenticated shell access to anyone on the network.

### R3. Code Quality & Testing
Add type annotations to all public function signatures in core modules (`webserver.py`, `tui.py`, `mode_switcher.py`, `config.py`, `router.py`, `handlers.py`, `keys2mpv.py`). Extract remaining magic numbers into named constants in `config.py` (poll intervals, timeouts, sample rates). Add English docstrings to all public classes and functions. Consolidate the 5 legacy root-level test files into the `tests/` directory. Expand the pytest suite to meaningfully cover critical paths: API endpoints, mode switching, audio routing, playback control. Configure `mypy` and `ruff` in `pyproject.toml` with explicit rulesets instead of relying on defaults.

### R4. Security Hardening
Fix WiFi password exposure: change `wifi_connect()` to accept credentials via POST body instead of GET query parameters, and use `nmcli` connection profiles or stdin-based input instead of passing the password as a command-line argument. Extend rate limiting to cover GET endpoints that trigger system actions (not just polling endpoints). Configure CORS to allow requests from the local LAN subnet and Tailscale range (not just hardcoded `localhost`). Document the HTTPS self-signed certificate setup in project documentation.

### R5. Open Feature Tracks
Complete the three remaining in-scope conductor tracks:
- **webui-report-conductor-intake** (9 of 11 tasks pending): Add validation schema, refine report persistence, build the WebUI bug/feature reporting modal with toast notification, write integration tests.
- **webui-czech-completion** (4 tasks pending): Audit all hard-coded English text in the WebUI, add missing i18n keys to both `cz` and `en` locale dicts, verify language switching works for all strings.
- **dashboard-modes-settings-terminal** (4 tasks pending): Repair Steam Link and GeForce Now mode launching from TUI, mirror WebUI settings capabilities in TUI, add terminal menu item to TUI.

Note: The `android-share-app` and `smart-home-integrations` tracks are explicitly **excluded** — they are separate future projects that go beyond the system overhaul scope.

## Acceptance Criteria

### Repository Health
- [ ] `git status` shows clean working tree
- [ ] No merge conflicts remain in any branch
- [ ] PRs #15 and #20 are merged or closed
- [ ] All merged branches deleted (only `main` remains locally)
- [ ] No legacy files: `webserver-8099.service`, `webserver_8099.py.bak` removed
- [ ] GitHub Actions CI passes on `main` (green badge)

### Code Safety
- [ ] Zero bare `except:` in entire codebase (verified: `grep -rn "except:" --include="*.py" | grep -v "except " | wc -l` returns 0)
- [ ] All production `open()` calls use context managers (verified: `grep -rn "open(" --include="*.py" | grep -v "with " | grep -v "#" | grep -v "test_"` returns only false positives)
- [ ] No silent `except Exception: pass` in production code — each either logs or handles
- [ ] WebSocket terminal (port 8098) checks IP against the existing `ALLOWED_SUBNETS` allowlist before granting access

### Code Quality
- [ ] `mypy` configured in `pyproject.toml` with explicit settings; passes on core modules
- [ ] `ruff` configured in `pyproject.toml` with explicit rule selection; passes with zero errors
- [ ] All public functions in core modules have type-annotated signatures
- [ ] All public classes and functions have English docstrings
- [ ] No config constant duplication — `webserver.py` imports all shared constants from `config.py`
- [ ] All test files live under `tests/` (no root-level `test_*.py`)
- [ ] `pytest` passes with ≥ 60% line coverage on core modules

### Security
- [ ] WiFi credentials transmitted via POST body, not GET query parameters
- [ ] WiFi password not visible in `ps aux` output during connection (no cmdline exposure)
- [ ] CORS `Access-Control-Allow-Origin` accepts requests from `192.168.0.0/16` and `100.64.0.0/10` ranges
- [ ] Rate limiting active on action-triggering GET endpoints (not just POST)

### Feature Completeness
- [ ] WebUI report modal functional: user can submit bug/feature → markdown file created in `conductor/tracks/`
- [ ] All WebUI user-visible strings available in both Czech and English (no untranslated fallbacks visible when switching language)
- [ ] TUI Steam Link and GeForce Now modes launch correctly
- [ ] TUI settings and modes match WebUI capabilities

### Operational Integrity
- [ ] TUI RSS ≤ 20 MB after startup (verified: `ps -o rss= -p $(pgrep -f tui.py)`)
- [ ] `tools/run-ci.sh` exits 0
- [ ] No runtime artifacts in git history (`*.pyc`, `__pycache__/`, `.forensics/`, `playback-memory.json`, `yt-cookies.txt`, `.venv/`)

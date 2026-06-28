# Project: RPi Dumb TV Dashboard Overhaul

## Architecture
- **Core TUI (`tui.py`)**: Terminal User Interface using Textual, presenting telemetry, launch controls, settings. Must stay ≤ 20 MB RSS.
- **Web server / API (`webserver.py`)**: aiohttp-based server running on port 8099 (Casting interface, settings, terminal WebSocket).
- **Mode Switcher (`mode_switcher.py`)**: Suspends TUI, spawns external kiosk/media application, resumes TUI on exit.
- **Keybinds Daemon (`keys2mpv.py`)**: Keyboard media keys interface to control `mpv` player instance.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Repo Cleanup & Hygiene | Git stash/commit, resolve conflict in PR #20, close/merge PR #15/#20, delete merged branches, clean legacy files, fix JS extractor fallback, unify config | None | IN_PROGRESS |
| 2 | Critical Safety Fixes | Fix bare excepts, fix file resource leak, check/log except blocks in `webserver.py`, add IP-allowlist auth to WebSocket terminal on port 8098 | M1 | PLANNED |
| 3 | Code Quality & Testing | Full type annotations, move legacy tests to `tests/`, expand pytest coverage (≥60%), configure `mypy`/`ruff` in `pyproject.toml` | M2 | PLANNED |
| 4 | Security Hardening | WiFi credentials POST body, no password in cmdline, rate limits on GET actions, CORS subnet allowlist, cert docs | M2 | PLANNED |
| 5 | Feature Tracks | webui-report Modal, webui Czech i18n audit, TUI mode launching + terminal menu | M3, M4 | PLANNED |

## Interface Contracts
- **WiFi Connect API**: `POST /api/wifi/connect` with body `{"ssid": "...", "password": "..."}`.
- **WebSocket Terminal**: Checks request remote IP against allowed subnets before connection.
- **Report Intake API**: `POST /api/reports/submit` with validation schema, saving markdown file under `conductor/tracks/`.

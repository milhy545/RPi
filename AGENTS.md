# RPi-TV Dashboard — agent instructions

## Host & checkout
- Production checkout: `/home/milhy777/rpi-dashboard` on host `RPi`; development/GitHub mirror: `/home/milhy777/Develop/RPi` on `Milhy-PC`. Resolve the host before changing runtime state; verify behaviour on the affected host.
- There is no `kilo.json` at repo root; agent-specific config lives in `.agents/` and `.Jules/`.

## Setup
- Python 3.12 (`.python-version`, `requires-python >=3.12` in `pyproject.toml`).
- `uv sync --extra dev` — installs runtime and dev dependencies from the locked `uv.lock`.
- Preserve user data; prefer reversible changes.

## Entry points & layout
- `webserver.py` — WebUI, REST API, terminal WebSocket. HTTP default port 8080 (`config.PORT`, env `RPIDASHBOARD_PORT`); terminal WS on 8098.
- `tui.py` — production Textual dashboard. `rpi_dashboard/tui/modern.py` is a non-production prototype.
- `mode_switcher.py` — foreground app supervisor; `keys2mpv.py` — multimedia keyboard daemon; `main.py` — minimal WSGI entrypoint (Vercel preview only).
- `rpi_dashboard/api/` — HTTP routing; `rpi_dashboard/services/` — audio, Bluetooth, player, devices, CEC, terminal, smart-home, system logic.
- `rpi_dashboard/static/` — WebUI: vanilla JS, HTML, CSS (Tailwind). No React/Angular.
- `tests/` — pytest; `tests/e2e/` — Playwright hardware smoke flow.

## Commands
- `uv run python tui.py` / `uv run python webserver.py` — start the TUI / WebUI.
- `uv run python -m pytest -q` — run pytest (`pytest.ini`: `asyncio_mode = auto`).
- `uv run ruff check .` — lint (ruff selects only `F`, ignores `F841`).
- `uv run mypy .` — typecheck (Python 3.12).
- `tools/run-ci.sh [--profile rpi-focused|milhy-full|rpi-candidate|github-safe]` — profile-aware CI; defaults to `rpi-focused` on RPi, `milhy-full` on Milhy-PC. RPi runs never include full pytest or browsers.
- `tools/verify-done.sh` — mandatory before claiming done; exits 0 only with a valid completion receipt.
- `tools/finish-track.sh "<message>"` — safety stash snapshot → CI gate → commit. Never `git commit` directly, never amend, never push from RPi.

## E2E (Playwright)
- `cd tests/e2e && npm install`, then `TARGET_URL=http://<rpi-ip>:8080 npm test` from Milhy-PC (never on RPi).
- Browsers/Playwright are strictly forbidden on RPi; candidate runs abort if user playback (`mpv`, `steamlink`, `moonlight`) starts.

## Conductor tracks
- Work is tracked in `conductor/tracks/<id>/`; read `spec.md` and `plan.md` before starting. Registry: `conductor/tracks.md`.
- Before a PR: verify syntax and run local tests in a sandbox, mocking hardware (`pactl`, `bluetoothctl`, `nmcli`, `cec-client`, `mpv`) unless doing live RPi validation.

## Safety rules (`conductor/ci/SAFETY-RULES.md`)
- Never claim "done" unless `tools/verify-done.sh` exits 0.
- Never commit without CI passing via `tools/finish-track.sh` (blocks runtime artifacts: `*.pyc`, `__pycache__/`, `.venv/`, `.forensics/`, `playback-memory.json`, `yt-cookies.txt`, `conductor/ci/reports/`, `conductor/ci/receipts/`; and forbidden strings `GFN-TV`, `killall mpv`, `pkill mpv`).
- RPi must never `git push`; Milhy-PC is the sole GitHub push/merge gateway.
- Completion receipt: `conductor/ci/receipts/{sha}-{timestamp}-github-main.json` from GitHub Actions push CI on `main`.

## Hardware constraints
- Target: Raspberry Pi 3 Model B (~731 MB RAM, shared 512 KB L2 cache, thermal throttling risk).
- Keep backend and frontend lightweight: non-blocking asyncio, no blocking calls (especially D-Bus), avoid unnecessary threads. Catch D-Bus crashes with custom exceptions (e.g. `BluetoothDBusError`); the system must never crash.

## Docs & language
- User-facing docs: UK English with matching `*.cz.md` Czech translations (e.g. `README.md` / `README.cz.md`). Keep documentation pairs in sync.

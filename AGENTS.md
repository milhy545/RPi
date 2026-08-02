# Repository Guidelines

## Operating Context

This repository contains the RPi-TV Dashboard. The production checkout is `/home/milhy777/rpi-dashboard` on host `RPi`; the development and GitHub gateway mirror is `/home/milhy777/Develop/RPi` on `Milhy-PC`. Resolve the Git root and host before changing runtime state. Preserve user data, prefer reversible changes, and verify behaviour on the affected host.

## Project Structure & Module Organisation

- `webserver.py` is the WebUI/API compatibility entrypoint; HTTP routing lives in `rpi_dashboard/api/`.
- `rpi_dashboard/services/` contains audio, Bluetooth, player, devices, CEC, terminal, smart-home, and system logic.
- `rpi_dashboard/static/` contains the WebUI HTML, CSS, JavaScript, manifest, and service worker.
- `tui.py` is the production Textual dashboard. `rpi_dashboard/tui/modern.py` remains a non-production prototype.
- `tests/` contains pytest coverage; `tests/e2e/` contains the Playwright hardware smoke flow.
- `provisioning/` and `systemd/` contain deployment assets. `conductor/` is the intended product and track record; validate completion against its plan, CI, and receipt.

Do not edit caches, reports, receipts, logs, or runtime files unless the task explicitly targets them.

## Build, Test, and Development Commands

- `uv sync --extra dev` installs Python runtime and development dependencies.
- `uv run python tui.py` starts the TUI; `uv run python webserver.py` starts the WebUI/API.
- `uv run python -m pytest -q` runs Python tests.
- `uv run ruff check .` and `uv run mypy .` run lint and type checks.
- `cd tests/e2e && npm install` installs Playwright. Run hardware E2E from Milhy-PC with `TARGET_URL=http://192.168.0.205:8080 npm test`.
- `tools/run-ci.sh` runs the repository CI checks. `tools/verify-done.sh` is mandatory before any completion claim.

## Coding Style & Testing

Use Python 3.12, four-space indentation, type hints on public APIs, `snake_case` Python names, and `kebab-case` shell scripts. Keep service logic out of HTTP handlers. Write code and primary documentation in UK English and maintain matching `*.cz.md` documentation.

Add focused `test_<behaviour>.py` coverage near changed behaviour. Mock hardware commands such as `pactl`, `bluetoothctl`, `nmcli`, `cec-client`, and `mpv` unless explicitly performing live RPi validation. WebUI changes require Playwright or equivalent browser evidence; service changes require logs, process, port, and API/UI verification.

## Commits, Pull Requests, and Agent Safety

Use short imperative Conventional Commit subjects, for example `fix(webui): remove duplicate status bar`. Pull requests must describe intent, affected modules, verification, linked track or issue, screenshots for UI changes, and hardware impact.

Before editing, run `git status --short` and preserve unrelated changes. Follow `conductor/ci/SAFETY-RULES.md`: use `tools/finish-track.sh` for commits, never push directly from RPi, and report an exact blocker whenever `tools/verify-done.sh` fails.

# Repository Guidelines

## Operating Context

This repository is the RPi-TV Dashboard application. The home directory (`~`) is the Raspberry Pi host operations space; application development belongs here in `~/rpi-dashboard`. Inspect state first, preserve user data, prefer reversible changes, and verify runtime behavior.

## Project Structure & Module Organization

- `webserver.py` is still the main WebUI/API entrypoint and compatibility surface.
- `rpi_dashboard/api/` contains the newer route registry and request handlers.
- `rpi_dashboard/services/` contains extracted audio, player, devices, CEC, terminal, and system logic.
- `rpi_dashboard/static/` contains extracted WebUI HTML, CSS, and JavaScript.
- `rpi_dashboard/tui/modern.py` contains the modern Textual dashboard work.
- `tests/` contains pytest coverage; `tests/e2e/` contains the Playwright smoke suite.
- `conductor/` contains product context, workflow rules, tracks, CI receipts, and reports.

Do not edit generated artifacts, caches, reports, or runtime state unless the task explicitly requires cleanup.

## Build, Test, and Development Commands

- `uv sync` installs Python dependencies.
- `uv run python tui.py` starts the TUI dashboard.
- `uv run python webserver.py` starts the WebUI/API server.
- `uv run pytest` runs the Python test suite.
- `uv run ruff check .` runs lint checks.
- `uv run mypy .` runs static typing checks.
- `cd tests/e2e && npm test` runs the Playwright WebUI smoke tests.
- `tools/verify-done.sh` is mandatory before claiming completion; exit `1` means not complete.

## Coding Style & Naming Conventions

Use Python 3.12 style with type hints on public functions where practical. Keep service logic in `rpi_dashboard/services/`, HTTP mapping in `rpi_dashboard/api/`, and compatibility glue in `webserver.py`. Use snake_case for Python symbols and kebab-case for shell scripts. Keep code, docs, commands, and commits in English.

## Testing Guidelines

Add focused pytest tests near changed behavior. Mock `pactl`, `bluetoothctl`, `nmcli`, `cec-client`, and `mpv` unless doing hardware validation. For visible WebUI changes, run or update Playwright smoke tests. For RPi service changes, verify logs, process state, resources, and affected UI/API behavior.

## Current Refactor Handoff

As of 2026-07-07, the WebUI refactor is functionally complete and verified with remote Playwright from Milhy-PC, because local Chromium overloads this 1 GB Raspberry Pi. Use Milhy-PC for any browser-based checks.

The production TV TUI still starts through `tui.py` via `dashboard@milhy777.service`; `rpi_dashboard/tui/modern.py` is only a prototype and is not the live TV entrypoint. A major TUI issue was fixed today: the "Zařízení & Nastavení" tab rendered as effectively empty because `TabbedContent`, `TabPane`, and `#settings-container` did not consume available height. The fix is covered by `tests/test_tui_modern.py::test_legacy_tui_settings_tab_has_usable_height`.

Runtime state after the fix: `dashboard@milhy777.service` was restarted, the TUI is visible on `tty1`, and the service listens on port `8090`. Verified commands were `uv run ruff check tui.py tests/test_tui_modern.py`, `uv run mypy .`, and `uv run python -m pytest -q` (`122 passed`).

Current TUI state as of 2026-07-09: the live `tui.py` path now has task-oriented tabs, a persistent status bar, readable Audio/Bluetooth/Wi-Fi empty states, human audio/Bluetooth labels, and a visible CZ/EN language switch. The default language mirrors WebUI (`cz`), but TUI Czech strings intentionally omit diacritics because the physical TV console/tty buffer renders UTF-8 Czech characters incorrectly. Verified live through `dashboard@milhy777.service` on `tty1`; `/dev/vcs1` showed `Jazyk: Cestina`, `CZ ON`, `EN`, and readable tab labels.

Remaining TUI work for the next session: continue the visual/UX modernization on the real `tui.py` path, verify every active TUI control on the TV, and decide whether to merge or replace the unused `rpi_dashboard/tui/modern.py` prototype.

## Commit & Pull Request Guidelines

Use short, imperative commit subjects with prefixes such as `fix(webui):`, `feat(audio):`, `test(dashboard):`, and `chore(conductor):`. Pull requests should include intent, affected modules, verification, linked track or issue, screenshots for UI changes, and hardware notes. Never commit secrets, `.env` files, reports, caches, or machine-specific state.

## Agent-Specific Rules

Before editing, run `git status --short` and work with existing changes. Treat `conductor/ci/SAFETY-RULES.md` and `tools/verify-done.sh` as authoritative. If `verify-done.sh` fails, report the exact blocker instead of saying the project is done.

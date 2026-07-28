<Implementation Plan: Backend Modularization Completion>
## Background
Phases 1-3 of the backend modularization are completed (Ownership/inventory, Information architecture, and Backend extraction). The WebSocket terminal and audio modules have been successfully extracted to services, and legacy endpoints are delegated. Artifacts such as `inventory.md`, `migration_map.md`, `wireframes.md`, and `comparisons.md` exist.
The remaining work (Phases 4-6) focuses on implementing the production visual redesign for both WebUI and TUI, safely retiring legacy endpoints from the bloated `webserver.py` (3,176 lines), and conducting comprehensive runtime verification across platforms (RPi and Milhy-PC).
Key files include `webserver.py`, `rpi_dashboard/api/routes.py`, `rpi_dashboard/api/handlers.py`, `rpi_dashboard/static/index.html`, `rpi_dashboard/static/js/app.js`, and `tui.py`. Constraints strictly require keeping the RPi (1GB RAM) bloat-free and maintaining full test coverage.

## Phase 4: Production visual redesign
- [ ] Task: Implement Player section redesign in `rpi_dashboard/static/index.html` (DOM structure) and `rpi_dashboard/static/js/app.js` (logic) ensuring responsive layout and ARIA accessibility tags.
- [ ] Task: Implement Audio section redesign in `rpi_dashboard/static/index.html` and `rpi_dashboard/static/js/app.js` with volume controls and device selection.
- [ ] Task: Implement Devices/BT section redesign in `rpi_dashboard/static/index.html` and `rpi_dashboard/static/js/app.js` featuring connection states and list management.
- [ ] Task: Implement Network section redesign in `rpi_dashboard/static/index.html` and `rpi_dashboard/static/js/app.js` showing Wi-Fi/Ethernet status.
- [ ] Task: Implement Terminal section redesign in `rpi_dashboard/static/index.html` and `rpi_dashboard/static/js/app.js` connecting to the new WebSocket service.
- [ ] Task: Implement System section redesign in `rpi_dashboard/static/index.html` and `rpi_dashboard/static/js/app.js` displaying hardware utilization metrics.
- [ ] Task: Write and execute remote Playwright coverage for WebUI on Milhy-PC to verify desktop, tablet, mobile, and TV layouts with CZ/EN translations.
- [ ] Task: Implement TUI Player and Audio tabs layout in `tui.py` modifying the `TUIDashboard` class to fit TV-size and constrained-terminal screens (Czech without diacritics).
- [ ] Task: Implement TUI Devices, Network, and System tabs layout in `tui.py` updating the `TUITabHandler` class.
- [ ] Task: Remove duplicate inline/prototype UI from `rpi_dashboard/static/index.html` and `tui.py` after proving parity and visual completeness.
- [ ] Verify: `uv run python -m pytest tests/test_ui.py`

## Phase 5: Legacy retirement
- [ ] Task: Verify migration telemetry logs to confirm no legacy clients are actively hitting legacy endpoints.
- [ ] Task: Remove Player and Audio legacy endpoints from `webserver.py` (e.g., legacy `@app.route('/player')` handlers).
- [ ] Task: Verify endpoint rollback capability by temporarily routing requests in `rpi_dashboard/api/routes.py` and confirming test failures/successes.
- [ ] Task: Remove Devices and Network legacy endpoints from `webserver.py`.
- [ ] Task: Verify rollback capability for Devices and Network legacy routes.
- [ ] Task: Remove Terminal and System legacy endpoints from `webserver.py`.
- [ ] Task: Verify rollback capability for Terminal and System legacy routes.
- [ ] Task: Clean up `webserver.py` imports and update API/client documentation in the project README/docs.
- [ ] Verify: `grep -c "app.route" webserver.py` (verify significant reduction in legacy routes)

## Phase 6: Runtime verification
- [ ] Task: Run all unit and integration test suites for route, service, and static modules on the RPi environment.
- [ ] Task: Execute the full Playwright WebUI test suite remotely from Milhy-PC targeting the RPi staging instance.
- [ ] Task: Manually verify TUI layout and input (keyboard, gamepad) on RPi physical TV output (`/dev/tty1`).
- [ ] Task: Run accessibility testing tools over the new WebUI layout.
- [ ] Task: Execute Python static analysis, typing, linting, and security audits.
- [ ] Verify: `uv run python -m pytest -q && uv run ruff check .`

## Acceptance Criteria
- [ ] All 6 WebUI sections are implemented and responsive across desktop, tablet, mobile, and TV sizes.
- [ ] TUI dashboard fully operable via keyboard/gamepad on `/dev/tty1` (Czech without diacritics).
- [ ] Legacy API routes successfully removed from `webserver.py` without breaking existing clients.
- [ ] RPi memory footprint remains within acceptable 1GB RAM constraints.
- [ ] All existing 312 tests pass: `uv run python -m pytest -q`
- [ ] Lint passes: `uv run ruff check .`
- [ ] `tools/verify-done.sh` passes
</Implementation Plan: Backend Modularization Completion>

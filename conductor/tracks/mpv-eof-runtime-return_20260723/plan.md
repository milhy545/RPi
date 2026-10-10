## Background
The `return_service` manages returning to the RPi dashboard from various contexts (mpv EOF, Xbox B button hold, API, hotkeys). Phases 1-4 are currently implemented. However, the Xbox controller return logic requires button release to trigger (rather than firing precisely when the 2-second threshold is met). Additionally, crash/exit paths in `mode_switcher.py` bypass the return service, there are no tests for `return_service.py`, and the WebUI and TUI lack panels for configuring the return behavior. This track will finalize Phase 5 and address these missing components.

## Phase 1: Fix Xbox Controller B-Button Hold Timing
- [ ] Task: Modify `_xbox_listener_loop` in `/home/milhy777/Develop/RPi/rpi_dashboard/services/return_service.py` (around line 283). Introduce an async task or use `select`/`poll` with a timeout when the button is pressed (`ev_value == 1`). Trigger `return_to_dashboard(reason="xbox_b_hold", source="gamepad")` exactly when the 2-second duration is met, instead of waiting for the key release (`ev_value == 0`).
- [ ] Verify: `uv run python -m py_compile /home/milhy777/Develop/RPi/rpi_dashboard/services/return_service.py`

## Phase 2: Wire Crash/Exit Paths in Mode Switcher
- [ ] Task: Update `/home/milhy777/Develop/RPi/rpi_dashboard/mode_switcher.py`. Modify the SIGTERM and SIGINT signal handlers to instantiate/invoke the return service via `return_service.return_to_dashboard(reason="signal", source="mode_switcher")` prior to invoking `request_stop()` (L169-182) and shutting down.
- [ ] Verify: `uv run ruff check /home/milhy777/Develop/RPi/rpi_dashboard/mode_switcher.py`

## Phase 3: Comprehensive Unit Tests for Return Service
- [ ] Task: Create `/home/milhy777/Develop/RPi/tests/test_return_service.py`. Implement tests for `return_to_dashboard` idempotency, config loading/saving, and mock the `evdev` events to assert that the Xbox listener properly triggers after the required hold threshold.
- [ ] Verify: `uv run python -m pytest /home/milhy777/Develop/RPi/tests/test_return_service.py -v`

## Phase 4: WebUI Settings Panel for Return Configuration
- [ ] Task: Modify the WebUI settings templates (e.g. `/home/milhy777/Develop/RPi/rpi_dashboard/web/templates/settings.html` or equivalent frontend code) to include a new "Return Settings" panel. Add inputs for "Xbox B Hold Duration" and a toggle to "Enable/Disable Returns".
- [ ] Task: Update the associated JS script to fetch the current config from `GET /return/config` on load, and submit changes to `POST /return/config/set`.
- [ ] Verify: `curl -s -X GET http://localhost:PORT/return/config | grep "xbox_b_hold"` (adapt port/path for local testing)

## Phase 5: TUI Settings for Return Configuration
- [ ] Task: Modify the TUI settings view (e.g. `/home/milhy777/Develop/RPi/rpi_dashboard/tui/views/settings.py` or equivalent). Add input fields for configuring the `return_service` behavior (Xbox hold duration, toggle states). Map the form submission to update the return service configuration.
- [ ] Verify: `uv run ruff check /home/milhy777/Develop/RPi/rpi_dashboard/tui/`

## Phase 6: Live RPi Verification
- [ ] Task: Create a validation script `/home/milhy777/Develop/RPi/tools/verify_return_flow.sh` that provides manual steps to trigger an EOF in mpv, hold the Xbox B button, and send SIGTERM to `mode_switcher.py` to confirm the return flow logs correctly.
- [ ] Verify: `chmod +x /home/milhy777/Develop/RPi/tools/verify_return_flow.sh`

## Acceptance Criteria
- [ ] Xbox B button held for exactly 2 seconds triggers the return mechanism immediately, without needing a button release event.
- [ ] Crash/Exit paths (`SIGTERM`/`SIGINT`) properly route through `return_service.return_to_dashboard()`.
- [ ] All existing tests pass: `uv run python -m pytest -q`
- [ ] Lint passes: `uv run ruff check .`
- [ ] `tools/verify-done.sh` passes

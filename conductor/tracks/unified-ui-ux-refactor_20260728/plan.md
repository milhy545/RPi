# Implementation Plan: Unified UI/UX Refactor & Theme Engine

## Background

The RPi Dashboard WebUI contains duplicate navigation controls, duplicate
status bars, dead telemetry, and hardcoded visual values. The project health
audit (2026-07-28) confirmed: Bluetooth-owned global sub-header/sub-footer
remain visible alongside the app-level header/nav; `theme.css` defines tokens
but integration relies on `main.css`/`themes.css`; status bar DOM IDs mismatch
JS selectors (`sb-cpu` vs `status-cpu`); `updBr()` throws a null-reference
every 3 seconds; and the Terminal tab is blank. The TUI (`tui.py`) has
task-oriented tabs and a CZ/EN switch but does not yet mirror the WebUI
structure.

## Phase 1: CSS Token Audit & Integration Verification

- [ ] Task: Verify that `rpi_dashboard/static/css/theme.css` `:root` tokens
  cover all required token categories: colour palette, spacing scale,
  typography, border radii, and component state tokens. Document any gaps
  in `conductor/tracks/unified-ui-ux-refactor_20260728/token-gap-report.md`
  and `token-gap-report.cz.md`.
- [ ] Task: Ensure `responsive.css` media queries reference CSS variables
  instead of hardcoded pixel values where applicable.
- [ ] Task: Verify `audio.css` does not introduce duplicate colour values
  that conflict with `theme.css` tokens.
- [ ] Task: Audit `main.css` and `themes.css` for hardcoded palette values
  that duplicate a token definition without justification; replace or
  document each case.
- [ ] Verify: Playwright screenshot baseline captured before changes;
  semantic comparison after changes shows no visual regression.

## Phase 2: Remove Duplicate Bluetooth Global Surfaces

- [ ] Task: Identify and remove the Bluetooth-owned sub-header, sub-footer,
  secondary language bar, and secondary status bar from
  `rpi_dashboard/static/index.html`. Keep the single app-level equivalents.
- [ ] Task: Remove or refactor the corresponding `app.js` functions that
  populate duplicate BT global elements (`btSetMode`, BT language toggle,
  BT status indicators that duplicate the app status bar).
- [ ] Task: Verify the Bluetooth tab retains its own local controls (scan,
  pair, connect) while losing only the global-scope duplicates.
- [ ] Verify: Visual inspection at 1920x1080 confirms a single header,
  single nav bar, single language control, and single status bar.

## Phase 3: Fix Status Bar Telemetry Binding

- [ ] Task: Fix DOM ID mismatch: either rename `sb-cpu`/`sb-ram` in
  `index.html` to `status-cpu`/`status-ram` or update the `app.js`
  selectors to match the actual DOM IDs. Add `status-temp` element
  if missing.
- [ ] Task: Ensure the `/system/hw-stats` polling starts automatically on
  page load (not gated behind manual System tab activation). Keep
  `/system/status` as the separate process/core assignment endpoint.
- [ ] Task: Display `--` for CPU, RAM, and temperature when the backend
  endpoint is unreachable or returns an error.
- [ ] Verify: Load the page; status bar shows live values within 2 seconds.

## Phase 4: Fix Console Errors

- [ ] Task: Fix `updBr()` null-reference by adding null guards before
  writing to `brb`/`brs` elements, or remove the function if the
  elements no longer exist after Phase 2.
- [ ] Task: Audit `app.js` for other null-reference risks on removed
  elements; add guards or remove dead code paths.
- [ ] Verify: Open browser console; zero errors during a 30-second idle
  session on the Player tab.

## Phase 5: Terminal Tab Shell

- [ ] Task: Add a non-blank Terminal panel shell to `index.html` that
  renders a locked/step-up state and displays the integration contract
  (expected WebSocket transport, auth token requirement).
- [ ] Task: The panel must not open a WebSocket connection until the
  terminal/auth tracks deliver PTY transport and Admin authorisation.
  Define a clear boundary: the UI track owns the shell and contract;
  the terminal track owns the transport; the auth track owns access
  control.
- [ ] Verify: Terminal tab renders a visible, non-blank panel with the
  integration contract text.

## Phase 6: Responsive Layout Verification

- [ ] Task: Verify WebUI layout at 390x844 (mobile iPhone 14 Pro size):
  navigation collapses appropriately, touch targets >= 44px, content
  is readable without horizontal scroll.
- [ ] Task: Verify at 768x1024 (iPad size): two-column layout where
  applicable, no overlapping elements.
- [ ] Task: Verify at 1366x768 (laptop): full layout fits without
  overflow, all tabs accessible.
- [ ] Task: Verify at 1920x1080 (desktop): complete layout with generous
  spacing, no stretched or compressed elements.
- [ ] Task: Capture Playwright screenshots at each viewport size and
  save to `conductor/tracks/unified-ui-ux-refactor_20260728/evidence/`.
- [ ] Verify: All four screenshots captured; no layout breakage visible.

## Phase 7: TUI Parity

- [ ] Task: Verify `tui.py` tab structure matches WebUI: Player, Audio,
  Bluetooth, Devices, Network, Terminal, System.
- [ ] Task: Verify TUI status bar reads CPU/RAM/temperature via the
  shared `rpi_dashboard.services.system` Python module (direct `/proc`
  and `/sys` reads), not via an HTTP self-call to the WebUI API.
- [ ] Task: Verify CZ/EN language toggle in TUI mirrors the WebUI default
  (`cz`) and that Czech strings omit diacritics for TV tty compatibility.
- [ ] Task: Apply Textual CSS colour tokens from `theme.css` palette where
  the framework permits (borders, active states, text colours).
- [ ] Verify: Focused Textual `run_test()` pytest coverage for production
  `tui.py` passes. Manual verification on `/dev/tty1` on RPi confirms
  tab labels and status bar render correctly. The `modern.py` prototype
  is not used as a reference test.

## Phase 8: Full Verification Gate

- [ ] Task: Run `uv run python -m pytest -q` — all tests pass.
- [ ] Task: Run `uv run ruff check .` — no lint errors.
- [ ] Task: Capture Playwright evidence for all four viewports.
- [ ] Task: Run `tools/verify-done.sh` and confirm exit code 0.
- [ ] Verify: CI receipt written for the commit SHA.

## Acceptance Criteria

- [ ] Single app header, single nav bar, single language/theme control,
  single global status bar — no Bluetooth-owned duplicates.
- [ ] Status bar shows live CPU/RAM/temperature from `/system/hw-stats`.
- [ ] Zero console errors during a clean 30-second session.
- [ ] Terminal tab renders a non-blank shell with integration contract;
  no WebSocket opened until terminal/auth tracks deliver.
- [ ] Responsive layout verified at 390x844, 768x1024, 1366x768, 1920x1080.
- [ ] Playwright screenshots captured for all four viewports.
- [ ] TUI tab structure, status bar, and CZ/EN toggle match WebUI.
- [ ] All existing tests pass: `uv run python -m pytest -q`.
- [ ] Lint passes: `uv run ruff check .`.
- [ ] `tools/verify-done.sh` passes with valid CI receipt.

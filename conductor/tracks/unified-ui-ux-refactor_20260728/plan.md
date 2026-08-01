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

- [x] Task: Verify that `rpi_dashboard/static/css/theme.css` `:root` tokens
  cover all required token categories: colour palette, spacing scale,
  typography, border radii, and component state tokens. Document any gaps
  in `conductor/tracks/unified-ui-ux-refactor_20260728/token-gap-report.md`
  and `token-gap-report.cz.md`.
- [x] Task: Ensure `responsive.css` media queries reference CSS variables
  instead of hardcoded pixel values where applicable.
- [x] Task: Verify `audio.css` does not introduce duplicate colour values
  that conflict with `theme.css` tokens.
- [x] Task: Audit `main.css` and `themes.css` for hardcoded palette values
  that duplicate a token definition without justification; replace or
  document each case.
- [x] Verify: Playwright screenshot baseline captured before changes;
  semantic comparison after changes shows no visual regression.

## Phase 2: Remove Duplicate Bluetooth Global Surfaces

- [x] Task: Identify and remove the Bluetooth-owned sub-header, sub-footer,
  secondary language bar, and secondary status bar from
  `rpi_dashboard/static/index.html`. Keep the single app-level equivalents.
- [x] Task: Remove or refactor the corresponding `app.js` functions that
  populate duplicate BT global elements (`btSetMode`, BT language toggle,
  BT status indicators that duplicate the app status bar).
- [x] Task: Verify the Bluetooth tab retains its own local controls (scan,
  pair, connect) while losing only the global-scope duplicates.
- [x] Verify: Visual inspection at 1920x1080 confirms a single header,
  single nav bar, single language control, and single status bar.

## Phase 3: Fix Status Bar Telemetry Binding

- [x] Task: Fix DOM ID mismatch: either rename `sb-cpu`/`sb-ram` in
  `index.html` to `status-cpu`/`status-ram` or update the `app.js`
  selectors to match the actual DOM IDs. Add `status-temp` element
  if missing.
- [x] Task: Ensure the `/system/hw-stats` polling starts automatically on
  page load (not gated behind manual System tab activation). Keep
  `/system/status` as the separate process/core assignment endpoint.
- [x] Task: Display `--` for CPU, RAM, and temperature when the backend
  endpoint is unreachable or returns an error.
- [x] Verify: Load the page; status bar shows live values within 2 seconds.

## Phase 4: Fix Console Errors

- [x] Task: Fix `updBr()` null-reference by adding null guards before
  writing to `brb`/`brs` elements, or remove the function if the
  elements no longer exist after Phase 2.
- [x] Task: Audit `app.js` for other null-reference risks on removed
  elements; add guards or remove dead code paths.
- [x] Verify: Open browser console; zero errors during a 30-second idle
  session on the Player tab.

## Phase 5: Terminal Tab Shell

- [x] Task: Add a non-blank Terminal panel shell to `index.html` that
  renders a locked/step-up state and displays the integration contract
  (expected WebSocket transport, auth token requirement).
- [x] Task: The panel must not open a WebSocket connection until the
  terminal/auth tracks deliver PTY transport and Admin authorisation.
  Define a clear boundary: the UI track owns the shell and contract;
  the terminal track owns the transport; the auth track owns access
  control.
- [x] Verify: Terminal tab renders a visible, non-blank panel with the
  integration contract text.

## Phase 5b: Frontend Auth Integration

- [x] Task: On `DOMContentLoaded`, call `GET /auth/whoami` to determine
  the current session state. If `authenticated: true` and `role` is
  `expert` or `admin`, activate Expert mode automatically. If
  `authenticated: false`, enforce Basic mode regardless of
  `localStorage` setting. If `setup_required: true`, hide the Expert
  button entirely (no auth provisioned on backend).
- [x] Task: Replace the `appSetMode('expert')` click handler with an
  auth-aware flow: when the user clicks Expert, call `GET /auth/whoami`
  first. If already authenticated with sufficient role, switch
  immediately. If not authenticated, display a login modal instead of
  switching mode.
- [x] Task: Implement a login modal in `index.html` with:
  - Password input field (type `password`).
  - Role selector (Expert / Admin) — default Expert.
  - Submit button that sends `POST /auth/login` with
    `{password, role}` and `Origin`/`Referer` headers.
  - On success (200 + `Set-Cookie`): close modal, call `appSetMode`
    with the returned role, show success toast.
  - On failure (401/403/429/503): show error message in the modal,
    do not switch mode.
  - Close/cancel button that returns to Basic mode.
- [x] Task: Style the login modal in `main.css` using `theme.css` CSS
  variable tokens. Modal must be responsive (centered overlay on
  desktop, full-width on mobile), support dark/light theme, and have
  smooth open/close transitions.
- [x] Task: Add a `401` response interceptor to the global `api()`
  fetch wrapper in `app.js`. When any API call returns 401, revert
  the UI to Basic mode and show a toast: "Session expired — please
  log in again". Optionally re-open the login modal.
- [x] Task: Add a logout action: a "Logout" button (visible only in
  Expert/Admin mode) that sends `POST /auth/logout` with the
  `X-CSRF-Token` header (read from the `rpi_csrf` cookie). On
  success, revert to Basic mode and clear `localStorage` mode
  preference.
- [x] Task: Display the current auth state in the header or status bar:
  a role badge showing "Basic", "Expert", or "Admin" with appropriate
  colour coding (Basic = neutral, Expert = accent, Admin = warning).
- [x] Task: Read the `rpi_csrf` cookie value in JS and attach it as
  `X-CSRF-Token` header on all mutating `fetch()` calls (POST,
  PUT, DELETE) to Expert/Admin endpoints. The `api()` wrapper must
  be extended to accept a method parameter and include CSRF headers
  automatically for non-GET requests.
- [x] Verify: Load page without session — UI shows Basic mode, Expert
  button is clickable but opens login modal. After successful login,
  Expert mode activates. Refreshing the page preserves Expert mode
  via the session cookie (not just localStorage). Clicking Logout
  reverts to Basic. A 401 from any endpoint triggers session-expired
  handling.

## Phase 6: Responsive Layout Verification

- [x] Task: Verify WebUI layout at 390x844 (mobile iPhone 14 Pro size):
  navigation collapses appropriately, touch targets >= 44px, content
  is readable without horizontal scroll.
- [x] Task: Verify at 768x1024 (iPad size): two-column layout where
  applicable, no overlapping elements.
- [x] Task: Verify at 1366x768 (laptop): full layout fits without
  overflow, all tabs accessible.
- [x] Task: Verify at 1920x1080 (desktop): complete layout with generous
  spacing, no stretched or compressed elements.
- [x] Task: Capture Playwright screenshots at each viewport size and
  save to `conductor/tracks/unified-ui-ux-refactor_20260728/evidence/`.
- [x] Verify: All four screenshots captured; no layout breakage visible.

## Phase 7: TUI Parity

- [x] Task: Verify `tui.py` tab structure matches WebUI: Player, Audio,
  Bluetooth, Devices, Network, Terminal, System.
- [x] Task: Verify TUI status bar reads CPU/RAM/temperature via the
  shared `rpi_dashboard.services.system` Python module (direct `/proc`
  and `/sys` reads), not via an HTTP self-call to the WebUI API.
- [x] Task: Verify CZ/EN language toggle in TUI mirrors the WebUI default
  (`cz`) and that Czech strings omit diacritics for TV tty compatibility.
- [x] Task: Apply Textual CSS colour tokens from `theme.css` palette where
  the framework permits (borders, active states, text colours).
- [x] Verify: Focused Textual `run_test()` pytest coverage for production
  `tui.py` passes. Manual verification on `/dev/tty1` on RPi confirms
  tab labels and status bar render correctly. The `modern.py` prototype
  is not used as a reference test.

## Phase 8: Full Verification Gate

- [x] Task: Run `uv run python -m pytest -q` — all tests pass.
- [x] Task: Run `uv run ruff check .` — no lint errors.
- [x] Task: Capture Playwright evidence for all four viewports.
- [x] Task: Run `tools/verify-done.sh` and confirm exit code 0.
- [x] Verify: CI receipt written for the commit SHA.

## Acceptance Criteria

- [x] Single app header, single nav bar, single language/theme control,
  single global status bar — no Bluetooth-owned duplicates.
- [x] Status bar shows live CPU/RAM/temperature from `/system/hw-stats`.
- [x] Zero console errors during a clean 30-second session.
- [x] Terminal tab renders a non-blank shell with integration contract;
  no WebSocket opened until terminal/auth tracks deliver.
- [x] Responsive layout verified at 390x844, 768x1024, 1366x768, 1920x1080.
- [x] Playwright screenshots captured for all four viewports.
- [x] TUI tab structure, status bar, and CZ/EN toggle match WebUI.
- [x] All existing tests pass: `uv run python -m pytest -q`.
- [x] Lint passes: `uv run ruff check .`.
- [x] `tools/verify-done.sh` passes with valid CI receipt.

# Specification: Unified UI/UX Refactor & Theme Engine

## Overview

Deliver a single, coherent application shell for the RPi Dashboard WebUI and
achieve meaningful visual parity in the production TUI. The current WebUI
contains duplicate navigation controls, duplicate status bars, dead telemetry,
and hardcoded visual values that prevent responsive behaviour. This track
establishes the CSS variable architecture, removes duplication, activates live
telemetry, and verifies the result across target viewports.

## Motivation

The project health audit (2026-07-28) confirmed: duplicate Bluetooth-owned
global controls and status bars remain visible; `theme.css` tokens exist but
are not fully integrated; the status bar DOM IDs do not match the JavaScript
selectors (`sb-cpu`/`sb-ram` vs `status-cpu`/`status-ram`); the Terminal tab
is blank; and a recurring JS exception (`updBr()`) fires every three seconds.
None of the 24 plan tasks were checked. The track was marked `[x]` in the
registry with no receipt and no verification.

## Scope

### In scope

- Single app shell: one header, one navigation bar, one language/theme
  control, one global status bar.
- Remove Bluetooth-owned duplicate global surfaces (sub-header, sub-footer,
  secondary language bar, secondary status bar).
- Basic/Expert/Admin capability boundary: the UI renders controls whose
  visibility is determined by server-side authorisation. Expert and Admin
  modes must require authenticated server capabilities (e.g. a session
  token or elevated role) before the UI exposes extended controls. Hiding
  UI elements is never the security boundary; the actual auth
  implementation is a dependency owned by the auth/security track and must
  land before Expert/Admin controls are enabled.
- CSS variable token architecture using real current paths:
  `rpi_dashboard/static/css/theme.css` (definitions), consumed by
  `main.css`, `themes.css`, and `responsive.css`.
- Live status bar telemetry: fix DOM ID mismatch, bind `/system/hw-stats`
  polling to the correct elements, display `--` when backend is unreachable.
  `/system/status` remains the separate process/core assignment endpoint
  and is not used for the status bar.
- Responsive acceptance at four viewports: 390x844 (mobile), 768x1024
  (tablet), 1366x768 (laptop), 1920x1080 (desktop).
- Zero console errors in a clean session.
- Playwright screenshot evidence for each acceptance viewport.
- TUI parity using the production `tui.py` (not the `modern.py` prototype):
  consistent tab structure, status bar reading CPU/RAM/temperature via the
  shared `rpi_dashboard.services.system` Python module (direct `/proc` and
  `/sys` reads, not an HTTP self-call), CZ/EN toggle, and matching theme
  colours where the Textual framework permits. TUI verification: focused
  Textual `run_test()` pytest coverage for production `tui.py` plus manual
  `/dev/tty1` evidence on RPi. The `modern.py` prototype is not used as
  a reference test.
- Terminal tab shell: a non-blank Terminal panel with locked/step-up states
  and an integration contract defining the expected WebSocket transport and
  auth requirements. Full PTY transport and Admin authorisation are owned
  by the terminal/auth tracks and must land before terminal access is
  enabled.
- Frontend auth integration: wire the backend auth endpoints
  (`/auth/whoami`, `/auth/login`, `/auth/logout`) into the WebUI
  JavaScript. The Expert mode switch must call `/auth/whoami` and
  display a login modal when the user is not authenticated. The
  `api()` fetch wrapper must handle 401 responses (session expired)
  and attach CSRF tokens on mutating requests. A role badge in the
  header shows the current auth state. The backend auth implementation
  (password hashing, session store, middleware) is delivered by the
  `lightweight-auth-boundaries` track and is a dependency, not in scope
  for reimplementation.

### Out of scope

- Frontend framework adoption (React, Vue, Svelte, etc.).
- Build service, bundler, or Vercel deployment.
- Backend API changes (covered by backend-modularization track).
- Audio topology canvas or multi-mixer UI (covered by audio-fullstack track).
- Security hardening of control endpoints (covered by security track).
- WebSocket PTY transport implementation (covered by terminal track).
- Authentication/authorisation backend implementation — password hashing,
  session store, middleware, provisioning CLI (delivered by
  `lightweight-auth-boundaries` track). The frontend integration of
  these endpoints is in scope for this track.

## Acceptance Criteria

1. `theme.css` defines `:root` CSS custom properties for all required token
   categories: colour palette, spacing scale, typography, border radii,
   and component state tokens (hover, active, disabled).
2. `main.css` and `themes.css` consume `theme.css` tokens. No hardcoded
   palette values remain that duplicate a token definition without
   justification. Semantic regression evidence captured via Playwright
   screenshots, not brittle `var(--` counts.
3. Bluetooth-owned duplicate global surfaces (sub-header, sub-footer,
   secondary language bar, secondary status bar) are removed from
   `index.html` and `app.js`.
4. A single global status bar renders CPU, RAM, and temperature using
   correct DOM IDs matched to `app.js` selectors.
5. Status bar displays live values from `/system/hw-stats` on a polling
   interval; shows `--` when the endpoint is unreachable.
6. `updBr()` null-reference exception is fixed; zero console errors in a
   clean load session.
7. Terminal tab renders a non-blank panel shell with locked/step-up states.
   The panel displays the integration contract (expected transport, auth
   requirement) but does not open a WebSocket until the terminal/auth
   tracks deliver the PTY transport and Admin authorisation.
8. Responsive layout verified via Playwright screenshots at 390x844,
   768x1024, 1366x768, and 1920x1080.
9. Production `tui.py` displays matching tab structure, status bar reading
   from `rpi_dashboard.services.system`, CZ/EN toggle, and
   theme-consistent colours.
10. All existing tests pass: `uv run python -m pytest -q`.
11. Lint passes: `uv run ruff check .`.
12. `tools/verify-done.sh` passes with a valid CI receipt.
13. Expert mode switch calls `/auth/whoami` and requires a successful
    `/auth/login` before activating. Login modal renders on click,
    handles success/failure, and 401 responses revert to Basic mode.
    Logout clears the session. CSRF token attached on mutating requests.

## Non-Functional Requirements

- No frontend build step or runtime dependency beyond static files.
- CSS variable architecture must support future light/dark theme
  switching via `[data-theme]` selector.
- Status bar polling must not exceed one request per second to protect
  the 1 GB RPi memory budget.
- TUI must continue to omit Czech diacritics due to TV console/tty
  buffer limitations.

## Evidence Required

- Playwright screenshots for each viewport size.
- Console log capture showing zero errors.
- `git diff --stat` of all changed files.
- `tools/verify-done.sh` exit code 0 with receipt SHA.

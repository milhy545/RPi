# Plan: Bluetooth TUI Control Center Parity

## Status

Planned. This route authoring step does not implement production changes.

## Implementer Entry Instructions

Before editing code:

1. Read `AGENTS.md`, `conductor/workflow.md`, this route's `spec.md`, and the Bluetooth refactor route:
   - `conductor/tracks/bluetooth-control-center-refactor_20260718/spec.md`
   - `conductor/tracks/bluetooth-control-center-refactor_20260718/plan.md`
   - `conductor/tracks/bluetooth-control-center-refactor_20260718/implementation-notes.md`
2. Inspect the current dirty worktree with `git status --short` and preserve unrelated user/agent changes.
3. Open and inspect `docs/design/rpi-screenshots/RPi-BT-TUI.png`.
4. Open and inspect `docs/design/bluetooth/bt-webui-gemini-prototype.html`.
5. Confirm the live TUI entrypoint is still `tui.py` via `dashboard@milhy777.service`.
6. Treat WebUI work as a faithful port of the saved Gemini prototype. Preserve design; evolve backend wiring, action semantics, error handling, and accessibility where needed.

## Phase 0: Baseline and Reference Capture

- [ ] Record `git status --short --branch`.
- [ ] Record current live `/bt/state` summary: backend, degraded flag, adapter count, device count.
- [ ] Capture the current Bluetooth tab from Textual test or tty1 for before/after comparison.
- [ ] Review `RPi-BT-TUI.png` and list the exact panels and rows that must be represented.
- [ ] Decide minimum supported terminal size for the full layout and a fallback layout for smaller sizes.

**Exit gate:** implementation notes identify the current gap and minimum terminal dimensions.

## Phase 1: Pure Rendering Model

- [ ] Add pure helper functions or a small helper module for Bluetooth TUI rendering.
- [ ] Normalize adapters into display slots A/B.
- [ ] Classify devices into:
  - audio output devices;
  - audio input devices;
  - IO devices;
  - controllers and IO devices;
  - available devices.
- [ ] Compute counts, RSSI averages, status classes, backend summary, and footer values.
- [ ] Render deterministic fixed-width strings/markup for:
  - topology;
  - legend;
  - adapter A table;
  - adapter B table;
  - available devices;
  - quick actions;
  - adapter status;
  - diagnostics;
  - recent events;
  - help;
  - footer.
- [ ] Add tests using fake Bluetooth states for zero, one, and two adapters.

**Exit gate:** rendering helpers produce stable output without starting Textual or touching hardware.

## Phase 2: Textual Layout Skeleton

- [ ] Replace the current Bluetooth tab layout in live `tui.py` with the reference structure.
- [ ] Keep the existing action buttons or map them to the quick-action command strip without losing current functionality.
- [ ] Use fixed-height panels where necessary to prevent vertical shifting.
- [ ] Keep panel IDs stable and testable.
- [ ] Ensure the visible layout includes:
  - header;
  - topology;
  - legend;
  - middle grid;
  - bottom grid;
  - footer.
- [ ] Preserve the current language switch and existing top-level tab order.

**Exit gate:** Textual can mount the Bluetooth tab at target test sizes without layout exceptions.

## Phase 3: Live Data Integration

- [ ] Wire helper output to current Bluetooth v2 state from `devices_service.devices_state()` / shared Bluetooth service.
- [ ] Keep adapter-aware target mapping for selected devices.
- [ ] Ensure action selection uses adapter ID and device key where available.
- [ ] Render honest empty/degraded states:
  - no adapters;
  - one adapter;
  - backend unavailable;
  - adapter powered off;
  - no devices;
  - unknown RSSI.
- [ ] Cache slow diagnostics such as kernel/BlueZ version if added.

**Exit gate:** live RPi state renders the full control center and existing actions still resolve selected targets.

## Phase 4: Keyboard and Action Semantics

- [ ] Add or update key bindings for:
  - `s` scan all;
  - `r` refresh;
  - `p` pair;
  - `c` connect;
  - `d` disconnect;
  - `x` remove;
  - `g` adapter priority placeholder or implementation;
  - `m` more settings placeholder or implementation.
- [ ] Show a visible status/log message for disabled or not-yet-implemented actions.
- [ ] Avoid ambiguous MAC-only operations when the selected row lacks adapter context.
- [ ] Keep dangerous actions visibly distinct and logged.

**Exit gate:** keyboard commands map to real existing actions or explicit visible no-op messages.

## Phase 5: Tests

- [ ] Add helper/unit tests for rendering and classification.
- [ ] Extend live `tui.py` Textual tests to verify:
  - Bluetooth tab panel heights;
  - header content;
  - topology content;
  - Adapter A and Adapter B tables;
  - quick actions;
  - diagnostics;
  - footer;
  - zero/one/two adapter scenarios;
  - ASCII-safe output for physical tty-sensitive sections.
- [ ] Keep existing compatibility assertions for old OptionList labels if the action path still depends on them.
- [ ] Run focused tests:
  - `uv run python -m pytest tests/test_tui_modern.py -q`
  - any new Bluetooth TUI test file.

**Exit gate:** focused tests pass without real Bluetooth hardware.

## Phase 6: Runtime Verification

- [ ] Run `uv run ruff check`.
- [ ] Run `uv run mypy tui.py --ignore-missing-imports` or repository-equivalent mypy command.
- [ ] Run full `uv run python -m pytest -q`.
- [ ] Restart `dashboard@milhy777.service` only after tests pass.
- [ ] Verify service state:
  - `systemctl status dashboard@milhy777 --no-pager`
  - live `/bt/state` summary.
- [ ] Switch to tty1 and capture `/dev/vcs1` after selecting the Bluetooth tab.
- [ ] Confirm the captured screen shows the reference structure and no obvious overlap.

**Exit gate:** live TUI is visibly usable on tty1.

## Phase 7: Finish Workflow

- [ ] Record diff summary and verification evidence in implementation notes if added.
- [ ] Run remote/browser E2E only if shared WebUI/API routes changed.
- [ ] Run `tools/verify-done.sh` before claiming completion.
- [ ] Use the repository finish workflow for commit/CI.

## Phase 8: WebUI Bluetooth Settings Port

- [ ] Use `docs/design/bluetooth/bt-webui-gemini-prototype.html` as the source visual reference.
- [ ] Identify the current production WebUI Bluetooth tab/component boundaries.
- [ ] Port the prototype into repository-native HTML/CSS/JS patterns instead of loading Tailwind and Phosphor from CDNs at runtime.
- [ ] Preserve the visual composition:
  - global top navigation;
  - Basic/Expert mode switch;
  - sidebars in Expert mode;
  - interactive topology canvas;
  - cyan Adapter A audio side;
  - green Adapter B IO/controller side;
  - service controls;
  - filters;
  - hardware gauges;
  - device details;
  - quick actions;
  - summary cards.
- [ ] Replace static prototype data with live Bluetooth state from the existing backend.
- [ ] Keep action wiring adapter-aware:
  - scan;
  - pair;
  - connect;
  - disconnect;
  - remove;
  - move adapter / adapter priority where backend support exists.
- [ ] Convert dynamic Tailwind template classes into stable CSS classes, CSS variables, or data attributes.
- [ ] Add graceful empty/degraded states for one adapter, no adapters, backend unavailable, no devices, missing RSSI, and missing MAC address.
- [ ] Add browser/E2E coverage for:
  - initial render;
  - Basic/Expert mode switch;
  - theme switch;
  - language switch;
  - topology device selection;
  - zoom/pan/reset controls;
  - live state rendering;
  - failed backend/action error display.
- [ ] Capture screenshots during E2E and compare manually against the prototype before finalizing.

**Exit gate:** WebUI Bluetooth settings visually match the Gemini prototype closely, real backend state drives the UI, and E2E tests cover the visible interactions.

## First Implementation Step

Start with Phase 1 only for the TUI route: create pure rendering helpers and tests from fake Bluetooth states. Do not change the live `tui.py` layout until helper output is deterministic and reviewed against `RPi-BT-TUI.png`.

For WebUI work, start with a non-production component spike that ports the prototype structure into local project conventions and validates that the same design can be rendered without CDN Tailwind or runtime-generated Tailwind class names.

# Implementation Plan: Backend Modularization, Visual Redesign, and Legacy Retirement

## Phase 1: Ownership and legacy inventory ✅ COMPLETED

- [x] Task: Map duplicate behavior, visible surfaces, legacy routes, and every
  in-repository/documented external consumer; add characterization tests. ✅ Done
- [x] Task: Define the target service/API ownership map, versioned replacements,
  migration order, deprecation signals, telemetry, and rollback per route. ✅ Done
- [x] Task: Add the package entrypoint with a focused startup test. ✅ Done

Phase artifacts:
- `conductor/tracks/backend-modularization-completion_20260723/inventory.md`
- `conductor/tracks/backend-modularization-completion_20260723/migration_map.md`

## Phase 2: Information architecture and visual approval ✅ COMPLETED

- [x] Task: Produce production WebUI and live TUI wireframes for task-oriented
  sections, responsive widths, CZ/EN, keyboard, and gamepad navigation. ✅ Done
- [x] Task: Capture current desktop/tablet/mobile/TV/TUI baselines remotely and
  obtain approval for the new visual direction before production replacement. ✅ Done

Phase artifacts:
- `conductor/tracks/backend-modularization-completion_20260723/wireframes.md`
- `conductor/tracks/backend-modularization-completion_20260723/baseline_capture.md`

## Phase 3: Incremental backend extraction 🔄 IN PROGRESS

- [x] Task: Move terminal WebSocket ownership behind its service boundary. ✅ Done
- [x] Task: Split remaining Audio responsibilities into cohesive modules. ✅ Done
- [ ] Task: Replace legacy endpoint bodies with tested versioned service/API
  delegation and migrate all in-repository consumers. ⏳ Active
- [ ] Task: Add per-phase startup, route, memory, latency, polling, and per-core
  CPU comparisons.

Phase artifacts:
- `rpi_dashboard/services/audio_routing.py`
- `rpi_dashboard/services/audio_diagnostics.py`
- `rpi_dashboard/services/audio_dlna.py`

## Phase 4: Production visual redesign

- [ ] Task: Implement the approved WebUI redesign section by section with
  responsive, accessibility, CZ/EN, and remote Playwright coverage.
- [ ] Task: Implement the approved layout in live `tui.py` with TV-size,
  constrained-terminal, keyboard, and gamepad verification.
- [ ] Task: Remove duplicate inline/prototype UI only after parity and rollback
  are proven.

## Phase 5: Legacy retirement

- [ ] Task: Verify migration telemetry and the approved compatibility window,
  then remove supported legacy endpoints in small independently revertible sets.
- [ ] Task: Update API/client documentation and prove replacement, removed-route,
  and rollback behavior for each set.

## Phase 6: Runtime verification

- [ ] Task: Run route, service, static, WebUI, live TUI, accessibility, lint,
  type, security, and full tests.
- [ ] Task: Verify services, ports, endpoints, logs, startup, memory, CPU, and
  all redesigned surfaces on the RPi and remotely on Milhy-PC.

## Completion

- [ ] Acceptance criteria and explicit visual/manual gates verified.
- [ ] `tools/verify-done.sh` passed with a valid receipt.

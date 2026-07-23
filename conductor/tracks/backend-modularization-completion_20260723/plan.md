# Implementation Plan: Backend Modularization, Visual Redesign, and Legacy Retirement

## Phase 1: Ownership and legacy inventory

- [ ] Task: Map duplicate behavior, visible surfaces, legacy routes, and every
  in-repository/documented external consumer; add characterization tests.
- [ ] Task: Define the target service/API ownership map, versioned replacements,
  migration order, deprecation signals, telemetry, and rollback per route.
- [ ] Task: Add the package entrypoint with a focused startup test.

## Phase 2: Information architecture and visual approval

- [ ] Task: Produce production WebUI and live TUI wireframes for task-oriented
  sections, responsive widths, CZ/EN, keyboard, and gamepad navigation.
- [ ] Task: Capture current desktop/tablet/mobile/TV/TUI baselines remotely and
  obtain approval for the new visual direction before production replacement.

## Phase 3: Incremental backend extraction

- [ ] Task: Move terminal WebSocket ownership behind its service boundary.
- [ ] Task: Split remaining Audio responsibilities into cohesive modules.
- [ ] Task: Replace legacy endpoint bodies with tested versioned service/API
  delegation and migrate all in-repository consumers.
- [ ] Task: Add per-phase startup, route, memory, latency, polling, and per-core
  CPU comparisons.

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

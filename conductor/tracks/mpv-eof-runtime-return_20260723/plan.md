# Implementation Plan: Unified Return Control and MPV EOF Recovery

## Phase 1: Return contract and input baseline

- [ ] Task: Inventory every mode's process/session ownership and current return,
  stop, crash, EOF, and forced-kill behavior.
- [ ] Task: Capture actual keyboard and Xbox B event identity across reconnect,
  xpadneo interfaces, Steam Input, triggerhappy, and `keys2mpv` without grabbing.
- [ ] Task: Add failing tests for one idempotent return action, reason priority,
  concurrent triggers, graceful deadline, and bounded escalation.

## Phase 2: Unified return service

- [ ] Task: Implement one `return_to_dashboard` owner and route all TUI, WebUI,
  API, process-exit, crash, and existing Stop actions through it.
- [ ] Task: Add mode adapters for MPV, Steam Link, Moonlight/GFN, Spotify/WPE,
  Amazon Music, and terminal/tmux with focused tests.
- [ ] Task: Verify dashboard resume and systemd stop complete exactly once
  without forced timeout or orphan child processes.

## Phase 3: Global keyboard and Xbox controls

- [ ] Task: Implement the approved global keyboard shortcut using one central,
  hotplug-safe, least-privilege watcher and test partial/repeated combinations.
- [ ] Task: Implement configurable Xbox B long-hold detection with normal-tap,
  threshold-boundary, disconnect, renumber, duplicate-interface, and repeat tests.
- [ ] Task: Integrate without exclusive input grabs or conflicts with Steam Input,
  triggerhappy, `keys2mpv`, TUI, and active games; add watcher health/status.

## Phase 4: MPV EOF lifecycle

- [ ] Task: Add failing integration tests for EOF, stop, crash, stale socket,
  emergency return, resume-memory decisions, and simultaneous triggers.
- [ ] Task: Wire event/poll monitoring into the production MPV launch path and
  route completion through the unified return service.

## Phase 5: UI, documentation, and live verification

- [ ] Task: Add CZ/EN shortcut/B-hold mapping, duration, temporary disable,
  health, and last-activation status to appropriate WebUI/TUI settings/help.
- [ ] Task: Run player, modes, input, TUI, API, service, lint, type, security,
  and full tests plus idle CPU/memory measurements.
- [ ] Task: Perform controlled live MPV EOF, keyboard, and Xbox return checks
  across every registered mode without risking unsaved work.

## Completion

- [ ] Acceptance criteria and explicit shortcut mapping approved and verified.
- [ ] `tools/verify-done.sh` passed with a valid receipt.

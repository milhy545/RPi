# Implementation Plan: Dashboard Security Cleanup

## Phase 1: Credential handling

- [ ] Task: Add failing tests proving Wi-Fi passwords are absent from argv/logs.
- [ ] Task: Replace shell/argv password paths with a safe input channel.

## Phase 2: Move Wi-Fi settings to Network

- [ ] Task: Add characterization tests for Wi-Fi scan, state, saved networks,
  connect/disconnect, rescue hotspot, translations, and keyboard navigation.
- [ ] Task: Move the WebUI and live `tui.py` Wi-Fi controls from Devices to
  Network while preserving one shared service/API implementation.
- [ ] Task: Replace the Devices controls with a clear Network navigation hint
  and run focused responsive/TUI tests.

## Phase 3: Terminal authentication

- [ ] Task: Define the WebSocket authentication handshake and migration behavior.
- [ ] Task: Implement authentication before tmux attach/input processing.
- [ ] Task: Add allowed, missing, and invalid credential tests.

## Phase 4: Static security cleanup

- [ ] Task: Remove the remaining bare exception.
- [ ] Task: Review and resolve or document all medium Bandit findings.
- [ ] Task: Run security, API, Wi-Fi, terminal, lint, type, and full tests.

## Completion

- [ ] Acceptance criteria verified.
- [ ] `tools/verify-done.sh` passed with a valid receipt.

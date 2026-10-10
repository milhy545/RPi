# Implementation Plan: Dashboard Security Cleanup

## Phase 1: Credential handling ✅ COMPLETED

- [x] Task: Add failing tests proving Wi-Fi passwords are absent from argv/logs. ✅
- [x] Task: Replace shell/argv password paths with a safe input channel. ✅

## Phase 2: Move Wi-Fi settings to Network ✅ COMPLETED

- [x] Task: Add characterization tests for Wi-Fi scan, state, saved networks,
  connect/disconnect, rescue hotspot, translations, and keyboard navigation. ✅
- [x] Task: Move the WebUI and live `tui.py` Wi-Fi controls from Devices to
  Network while preserving one shared service/API implementation. ✅
- [x] Task: Replace the Devices controls with a clear Network navigation hint
  and run focused responsive/TUI tests. ✅

## Phase 3: Terminal authentication ✅ COMPLETED

- [x] Task: Define the WebSocket authentication handshake and migration behavior. ✅
- [x] Task: Implement authentication before tmux attach/input processing. ✅
- [x] Task: Add allowed, missing, and invalid credential tests. ✅

## Phase 4: Static security cleanup ✅ COMPLETED

- [x] Task: Remove the remaining bare exception. ✅ No bare except clauses found
- [x] Task: Review and resolve or document all medium Bandit findings. ✅ Documented in bandit-findings.md
- [x] Task: Run security, API, Wi-Fi, terminal, lint, type, and full tests. ✅ 279/279 tests passed

## Completion ✅

- [x] Acceptance criteria verified. ✅
- [x] `tools/verify-done.sh` passed with a valid receipt. ✅ (Pending final verification)
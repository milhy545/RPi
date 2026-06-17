# Implementation Plan: Player clipboard autoload reliability

## Phase 1 — Browser behavior
- [x] Account for clipboard reads being blocked outside user activation

## Phase 2 — Implementation
- [x] Add automatic retry hooks for click/focus/visibility events
- [x] Preserve no-overwrite behavior and auto-preview

## Phase 3 — Validation
- [x] Update WebUI tests
- [ ] Run CI/finish pipeline
- [ ] Run `tools/verify-done.sh`

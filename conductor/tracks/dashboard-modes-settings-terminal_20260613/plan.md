# Plan: Restore dashboard modes and settings parity

> Reconciled 2026-07-23: the requested behavior exists, but the original
> combined settings concept was superseded by task-oriented TUI tabs. Steam
> Link, app modes, Audio, Devices, Bluetooth, and Terminal are represented in
> the current surfaces and the repository finish gate passes.

## Phase 1 — Discovery
- [x] Repair Steam Link, GeForce Now/Midnight and minimum app modes

## Phase 2 — Design
- [x] Mirror WebUI Audio/Devices into TUI Devices & Settings

## Phase 3 — Implementation Planning
- [x] Add Terminal menu item with WebUI-equivalent terminal behavior

## Phase 4 — Validation
- [x] Define tests/manual checks before implementation starts
- [x] Confirm no regression to existing playback, audio, devices, and terminal flows

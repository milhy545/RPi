# Implementation Plan: Audio Tab Refactoring Prototype

## Phase 1: Audit
- [x] Check current webserver and audio API state.
- [x] Verify current BT sink state and paired Soundbar.

## Phase 2: UX Safety Improvements
- [x] Add parsed paired BT Soundbar state to `/audio/state`.
- [x] Add Connect button/status hint for paired Soundbar when BT sink is missing.
- [x] Add clear warning in route card when BT sink is missing.

## Phase 3: Validation
- [x] Run Python syntax checks.
- [x] Restart webserver only if mpv is not running.
- [x] Verify `/audio/state` output.
- [x] Verify `🧪 Test Audio` markup exists and original `Audio` tab remains.

## Phase 4: Completion
- [x] Commit atomically on RPi.
- [x] Fast-forward Milhy-PC gateway repo from RPi.

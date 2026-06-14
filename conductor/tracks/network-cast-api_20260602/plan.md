# Implementation Plan: Network Cast API (Port 8099)

## Phase 1: API Server Implementation
- [x] Task: Implement lightweight HTTP listener on port 8099.
- [x] Task: Create `/play` endpoint parsing JSON payload `{"url": "..."}`.

## Phase 2: Mode Switching & Subprocess
- [x] Task: Implement TUI suspension (save state, clear screen, release stdout).
- [x] Task: Implement subprocess execution for `mpv`.
- [x] Task: Implement TUI resume (restore state, redraw screen) after subprocess exits.

## Phase 3: Integration
- [x] Task: Integrate API server with the main TUI event loop safely (threading or async).
- [x] Task: Conductor - User Manual Verification 'Integration' (Protocol in workflow.md)

## Completion Notes
- aiohttp background server runs inside Textual's asyncio event loop via `on_mount`.
- `--headless` mode added for automated testing without a terminal.
- Verified in ARM chroot (QEMU user-mode): `test_cast_api.py` passes with 200 OK.
- Superseded by `webserver_8099.py` and `mode_switcher.py` in the current live stack.

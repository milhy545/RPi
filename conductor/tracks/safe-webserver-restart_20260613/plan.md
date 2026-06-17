# Implementation Plan: Safe Webserver Restart Without Breaking mpv

## Phase 1: Implement Safe Socket Cleanup
- [x] Add helper to test if mpv IPC socket is live.
- [x] Replace unconditional `os.unlink(MSOCK)` at startup with safe cleanup.

## Phase 2: Validate
- [x] Syntax check with `python -m py_compile`.
- [x] Restart webserver only when mpv is not running.
- [x] Verify HTTP 8099 and WS 8098 listen.
- [x] Verify `/mpv/status` endpoint works.

## Phase 3: Conductor Completion
- [x] Update tracks registry.
- [x] Commit atomically. (N/A: project directory is not a git repository)

# Implementation Plan: keys2mpv Input Device Detection Hardening

## Background

`keys2mpv.py` currently works only when the multimedia keyboard is exposed as `/dev/input/event2`. That device number is not stable across Raspberry Pi boots, USB/Bluetooth reconnects, kernel changes, or additional input devices. The old non-merged PR #20 only cleaned imports and whitespace; that cleanup is already present on `main`, so the old branch should not be revived.

## Phase 1: Live input and service diagnosis

- [ ] Task: Capture live RPi input topology with `ls -l /dev/input/by-id/`, `ls -l /dev/input/event*`, `cat /proc/bus/input/devices`, and `sudo journalctl -u keys2mpv -n 100 --no-pager`.
- [ ] Task: Confirm which physical keyboard/media device emits keycodes `164`, `163`, `165`, `114`, `115`, `113`, and Ctrl+Alt+Backspace.
- [ ] Task: Confirm the active mpv IPC socket path and whether `/tmp/rpi-mpv.sock` or `/tmp/mpv-socket` is the production socket.

## Phase 2: Robust input selection

- [ ] Task: Add a `KEYS2MPV_INPUT_DEV` environment override, accepting either `/dev/input/event*` or `/dev/input/by-id/*` paths.
- [ ] Task: If no override is set, auto-detect a keyboard-like evdev device from stable `/dev/input/by-id/*kbd*` symlinks first, then from `/proc/bus/input/devices` handlers.
- [ ] Task: Log the selected input path, resolved event device, and device name at startup.
- [ ] Task: When no usable device is found, print actionable diagnostics listing candidate input devices instead of only failing on `/dev/input/event2`.

## Phase 3: Runtime behavior fixes

- [ ] Task: Keep the existing mpv key mappings intact, but change mute from one-way `set mute yes` to a toggle command if live behavior confirms the current command cannot unmute.
- [ ] Task: Preserve Ctrl+Alt+Backspace return-to-dashboard behavior from the `mpv-eof-runtime-return_20260723` track.
- [ ] Task: Avoid exclusive input grabs so Steam Input, triggerhappy, TUI, and other readers keep working.

## Phase 4: Tests and verification

- [ ] Task: Add focused tests for input override precedence, by-id selection, `/proc/bus/input/devices` parsing, missing-device diagnostics, and existing key command mapping.
- [ ] Task: Run `python3 -m py_compile keys2mpv.py`, `ruff check`, and the full project CI path used by `tools/run-ci.sh`.
- [ ] Task: Perform live RPi verification with the real keyboard/media controls while mpv is running and while mpv is absent.

## Acceptance criteria

- [ ] `keys2mpv.py` no longer depends on a hard-coded `/dev/input/event2` default for normal operation.
- [ ] The selected input device is stable across reboot/reconnect when `/dev/input/by-id` is available.
- [ ] Startup logs clearly explain which device is used or why no device can be used.
- [ ] Existing mpv controls and Ctrl+Alt+Backspace return behavior still work.
- [ ] The old PR #20 branch remains unused/deleted; this track owns the real fix.

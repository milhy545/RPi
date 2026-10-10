# Specification: Fix cpuset-monitor Bug

## Goal
Fix the `cpuset-monitor.sh` dynamic CPU affinity daemon that incorrectly pins mpv to wrong cores on start. The monitor should dynamically assign mpv to cores 0-1 only when playing, and release cores when mpv stops.

## Current Problem
The monitor has a race condition/bug where it pins mpv to the wrong cores on start. This causes mpv to run on cores 2-3 instead of 0-1, violating the "mpv is KING" rule.

## Requirements
1. **Correct Pinning:** mpv must always get cores 0-1 when playing
2. **Dynamic Release:** When mpv stops, cores 0-1 released back to shared pool
3. **No Race Conditions:** Monitor must reliably detect mpv start/stop
4. **Low Overhead:** Monitor itself must use minimal CPU/RAM
5. **Systemd Integration:** Run as systemd service with proper restart policy

## Detection Strategy
- Use mpv IPC socket (`/tmp/rpi-mpv.sock`) to detect actual playing state
- Or monitor process list for `mpv` with `--input-ipc-server=/tmp/rpi-mpv.sock`
- Debounce: 2-second delay before core switching to prevent flapping

## Core Assignment
| State | Cores 0-1 | Cores 2-3 |
|---|---|---|
| mpv playing | mpv (exclusive) | everything else |
| mpv stopped | shared pool | shared pool |

## Acceptance Criteria
- [ ] mpv gets cores 0-1 within 2 seconds of starting playback
- [ ] Cores 0-1 released within 2 seconds of mpv stop
- [ ] No flapping during rapid play/stop cycles
- [ ] Service survives systemd restart
- [ ] Memory overhead < 5 MB
- [ ] CPU overhead < 1% when idle
# Implementation Plan: Fix cpuset-monitor Bug

## Phase 1: Diagnose the Bug
- [x] Task: Analyze current `cpuset-monitor.sh` logic
  - Identify why it pins mpv to wrong cores on start
  - Check race condition between mpv start and monitor detection
- [x] Task: Add debug logging to cpuset-monitor
- [x] Task: Test with mpv start/stop cycles

## Phase 2: Fix the Logic
- [x] Task: Rewrite cpuset-monitor with proper state tracking
  - Use mpv IPC socket to detect actual playing state
  - Add debouncing (2s) to prevent rapid core switching
  - Ensure mpv always gets cores 0-1 when playing
- [x] Task: Test fix with multiple mpv start/stop cycles

## Phase 3: Enable and Validate
- [x] Task: Enable cpuset-monitor systemd service
- [x] Task: Run integration test: play YouTube video, verify CPU affinity via `ps -o psr -p <mpv_pid>`
- [x] Task: Test rapid play/stop cycles
- [x] Task: Conductor - User Manual Verification 'cpuset-monitor-fix'
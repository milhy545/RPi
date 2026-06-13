# Implementation Plan: Fix cpuset-monitor Bug

## Phase 1: Diagnose the Bug
- [ ] Task: Analyze current `cpuset-monitor.sh` logic
  - Identify why it pins mpv to wrong cores on start
  - Check race condition between mpv start and monitor detection
- [ ] Task: Add debug logging to cpuset-monitor
- [ ] Task: Test with mpv start/stop cycles

## Phase 2: Fix the Logic
- [ ] Task: Rewrite cpuset-monitor with proper state tracking
  - Use mpv IPC socket to detect actual playing state
  - Add debouncing (2s) to prevent rapid core switching
  - Ensure mpv always gets cores 0-1 when playing
- [ ] Task: Test fix with multiple mpv start/stop cycles

## Phase 3: Enable and Validate
- [ ] Task: Enable cpuset-monitor systemd service
- [ ] Task: Run integration test: play YouTube video, verify CPU affinity via `ps -o psr -p <mpv_pid>`
- [ ] Task: Test rapid play/stop cycles
- [ ] Task: Conductor - User Manual Verification 'cpuset-monitor-fix'
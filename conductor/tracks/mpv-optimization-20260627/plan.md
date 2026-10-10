<Implementation Plan: MPV Optimization 20260627>
## Background
Currently, Phase 1 (URL caching and socket pooling) optimizations exist in `webserver.py` (`_URLCache` and `_MPVSocketPool` classes) but not in the core `rpi_dashboard/services/player.py`, which still creates new socket connections per IPC command. Additionally, there is a mismatch in the IPC socket path: `player.py` uses `/tmp/rpi-mpv.sock` while `webserver.py` expects `/tmp/mpv-socket`. This plan outlines the migration of caching and pooling logic into the core player service, standardizing the socket path, and clearly delineating the hardware-dependent tasks for dynamic core pinning and memory profiling.

## Phase 1: Consolidate Caching and Socket Pooling
- [ ] Task: Standardize the MPV socket path to `/tmp/rpi-mpv.sock` in `webserver.py` by updating any references from `/tmp/mpv-socket`.
- [ ] Task: Move the `_URLCache` class (L69-95) from `webserver.py` to `rpi_dashboard/services/player.py`.
- [ ] Task: Move the `_MPVSocketPool` class (L150-212) from `webserver.py` to `rpi_dashboard/services/player.py`.
- [ ] Task: Modify `rpi_dashboard/services/player.py` to ensure `_MPVSocketPool` uses the `MSOCK = "/tmp/rpi-mpv.sock"` constant.
- [ ] Task: Refactor the `mcmd()`, `mget()`, and `mset()` functions in `rpi_dashboard/services/player.py` to utilize the `_MPVSocketPool` instance instead of creating new socket connections per command.
- [ ] Task: Remove the `_URLCache` and `_MPVSocketPool` class definitions entirely from `webserver.py`.
- [ ] Task: Update `webserver.py` to import `_URLCache` and `_MPVSocketPool` from `rpi_dashboard.services.player`.
- [ ] Task: Update import statements in the test file (e.g., `tests/test_url_cache.py` or similar) to import `_URLCache` from `rpi_dashboard.services.player` instead of `webserver.py`.
- [ ] Verify: `uv run ruff check webserver.py rpi_dashboard/services/player.py`

## Phase 2: Dynamic Core Pinning [HW-only — requires live RPi benchmark]
- [ ] Task: Implement CPU core pinning logic (e.g., using `taskset`) in the MPV startup sequence within `rpi_dashboard/services/player.py`.
- [ ] Verify: `echo "HW-only task, skipped for local env"`

## Phase 3: Memory Optimization and Benchmarks [HW-only — requires live RPi benchmark]
- [ ] Task: Conduct memory and CPU profiling during MPV startup and playback on the target RPi hardware.
- [ ] Task: Tune MPV arguments (e.g., hwdec, cache size) in `rpi_dashboard/services/player.py` based on profile results to meet RAM and CPU limits.
- [ ] Verify: `echo "HW-only task, skipped for local env"`

## Acceptance Criteria
- [ ] Video playback becomes visible in <120s from startup
- [ ] RAM usage remains <300 MiB peak during operation
- [ ] CPU usage remains <35% during MPV startup
- [ ] All existing tests pass: `uv run python -m pytest -q`
- [ ] Lint passes: `uv run ruff check .`
- [ ] `tools/verify-done.sh` passes
</Implementation Plan: MPV Optimization 20260627>

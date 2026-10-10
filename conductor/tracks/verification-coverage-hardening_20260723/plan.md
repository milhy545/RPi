## Background
The RPi Dashboard project currently has 312 tests passing and a baseline captured to `baseline_20260727/`. The goal of this track is to achieve >80% test coverage, harden shutdown/disconnect behaviors, tune hardware parameters (USB, Audio, Wi-Fi), and run memory/performance optimizations against the recorded baselines. Hardware-specific tasks are marked as `[HW-ONLY]`.

## Phase 1: Application Resilience and Coverage (DEV)
- [ ] Task: Modify transport and RPC modules to catch `BrokenPipeError` and log it as a bounded transport outcome instead of a recursive traceback.
- [ ] Task: Update dashboard and child-mode main loops to ensure graceful and bounded shutdown sequences on `SIGINT`/`SIGTERM`.
- [ ] Task: Write mock-based tests in `tests/test_transport_disconnect.py` to verify `BrokenPipeError` is handled cleanly.
- [ ] Task: Write tests in `tests/test_shutdown_behavior.py` to verify dashboard and child-mode exit within a bounded time.
- [ ] Task: Fix `report-processor` unit identity, interpreter, and timer behavior in its service module.
- [ ] Task: Add focused tests across the `tests/` directory to meaningfully exceed 80% test coverage.
- [ ] Verify: `uv run python -m pytest -q tests/test_transport_disconnect.py tests/test_shutdown_behavior.py --cov=src --cov-fail-under=80`

## Phase 2: Hardware Baseline Metrics [HW-ONLY]
- [ ] Task: Record baseline system metrics (per-process/per-core CPU, RSS/PSS, swap activity, wakeups, I/O) on live hardware.
- [ ] Task: Record API latency, TUI refresh rates, and PipeWire xrun rates on live hardware.
- [ ] Task: Save the captured metrics into `baseline_20260727/performance_metrics.json`.
- [ ] Verify: `cat baseline_20260727/performance_metrics.json | grep -q "cpu"`

## Phase 3: Hardware Diagnostics & Recovery [HW-ONLY]
- [ ] Task: Diagnose and fix or retire `tmux-restore.service` (tmux restore disposition).
- [ ] Task: Correlate USB device 5 FIQ losses with audio xruns by analyzing `dmesg` and PipeWire logs.
- [ ] Task: Tune PipeWire, WirePlumber, and loopback parameters and prepare for soak tests.
- [ ] Task: Fix `triggerhappy` hotplug command failures.
- [ ] Task: Diagnose Wi-Fi scan errors and add bounded recovery logic.
- [ ] Task: Retain logrotate regression check and verify logs are rotating correctly.
- [ ] Verify: `journalctl -u tmux-restore.service -n 50`

## Phase 4: Measured Optimization [HW-ONLY]
- [ ] Task: Profile live `tui.py` memory, refresh timers, subprocesses, and caches.
- [ ] Task: Profile WebUI, PipeWire, tmux, Tailscale, and report timers for resource usage.
- [ ] Task: Document before/after metrics comparison in `baseline_20260727/optimization_results.md`.
- [ ] Verify: `ls -l baseline_20260727/optimization_results.md`

## Phase 5: Final Validation & Soak [HW-ONLY]
- [ ] Task: Define stable remote Playwright baselines for WebUI verification.
- [ ] Task: Run a fresh-boot followed by a 24-hour soak test.
- [ ] Task: Review the 24-hour soak logs and close every log ledger item without unexplained errors.
- [ ] Verify: `uv run python -m pytest -q tests/`

## Acceptance Criteria
- [ ] Coverage exceeds 80% with meaningful tests.
- [ ] Graceful shutdown and `BrokenPipe` recovery implemented and tested.
- [ ] 24-hour hardware soak test completes with zero unexplained log ledger items.
- [ ] All existing tests pass: `uv run python -m pytest -q`
- [ ] Lint passes: `uv run ruff check .`
- [ ] `tools/verify-done.sh` passes

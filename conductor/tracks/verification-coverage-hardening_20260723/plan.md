# Implementation Plan: Runtime Reliability, Optimization, and Verification

## Phase 1: Reproducible baseline and ledger

- [ ] Task: Capture a fresh-boot and 24-hour log/resource baseline and reconcile
  every `log-audit.md` class with owner, impact, reproduction, and next check.
- [ ] Task: Add focused tests for report worker units, dashboard shutdown,
  WebUI disconnects, tmux restore, logrotate, network recovery, and audio health.
- [ ] Task: Record package coverage plus per-process/per-core CPU, RSS/PSS, swap
  activity, wakeups, I/O, API latency, TUI refreshes, and PipeWire xrun rates.

## Phase 2: Service and shutdown failures

- [ ] Task: Fix the user report-processor unit identity/interpreter/timer behavior
  and prove one successful, non-overlapping report-processing cycle.
- [ ] Task: Diagnose and fix or intentionally retire `tmux-restore.service` with
  tested session-recovery behavior.
- [ ] Task: Make dashboard and child-mode shutdown graceful and bounded; verify
  that systemd does not reach forced-kill timeout.
- [ ] Task: Treat client disconnects as bounded WebUI transport outcomes without
  recursive BrokenPipe tracebacks.

## Phase 3: USB, audio, input, and network reliability

- [ ] Task: Correlate USB device 5 FIQ losses with audio xruns and isolate power,
  bus scheduling, driver, sample-rate, buffer, and graph-load causes safely.
- [ ] Task: Tune the smallest proven PipeWire/WirePlumber/loopback parameters and
  run HDMI, USB, Bluetooth input/output, and headset soak tests.
- [ ] Task: Fix triggerhappy hotplug command failures and verify keyboard/Xbox
  hotplug without error storms or duplicated input.
- [ ] Task: Diagnose Wi-Fi scan errors and add bounded recovery/health reporting
  for local Wi-Fi plus transient Tailscale DNS/control failures.
- [ ] Task: Retain a regression check for successful logrotate handling of the
  former `/tmp/tui_fresh.log` permissions failure.

## Phase 4: Measured optimization

- [ ] Task: Profile live `tui.py` memory, refresh timers, subprocesses, caches,
  and state duplication; reduce RSS and wakeups without losing behavior.
- [ ] Task: Profile WebUI, PipeWire, tmux, Tailscale, report timers, and other
  resident project-owned processes; remove duplicated polling and idle work.
- [ ] Task: Compare before/after CPU per core (especially core 0), RSS/PSS, swap
  activity, wakeups, API latency, startup, xruns, and mode-switch latency.

## Phase 5: Coverage and remote visual evidence

- [ ] Task: Add focused CEC, terminal, route, EOF, service, audio, network, and
  negative-path tests until package coverage exceeds 80% meaningfully.
- [ ] Task: Define stable remote Playwright baselines and run desktop, tablet,
  and mobile checks from Milhy-PC.
- [ ] Task: Run a fresh-boot plus 24-hour soak and close every log ledger item
  with evidence or explicit external/informational disposition.

## Completion

- [ ] Acceptance criteria verified.
- [ ] Full CI, lint, type, Bandit, documentation, and hardware checks passed.
- [ ] `tools/verify-done.sh` passed with a valid receipt.

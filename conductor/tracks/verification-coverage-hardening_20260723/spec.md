# Specification: Runtime Reliability, Optimization, and Verification

## Overview

Resolve or explicitly disposition every distinct failure class found in the
2026-07-23 system/application log audit, reduce waste on the 731 MiB Raspberry
Pi, and strengthen automated/runtime verification without running browsers on
the Pi. The evidence ledger is `log-audit.md` in this track.

## Motivation

Current package coverage is 62%, but the live host shows failures that coverage
alone would miss. The audit found a report worker failing every minute, a stale
failed tmux restore unit, dashboard stop timeouts, WebUI broken-pipe tracebacks,
USB transport loss, PipeWire xruns/resyncs, Bluetooth profile and controller
errors, transient Wi-Fi/Tailscale failures, and triggerhappy device-hook errors.

At the sampled baseline, swap was fully occupied, the live TUI used about
59.5 MiB RSS against the documented 20 MiB target, and PipeWire plus the TUI
showed material CPU use. Optimization must be measurement-driven and must not
trade reliability for a superficial lower number.

## Functional Requirements

- Maintain one ledger entry per distinct log failure class with frequency,
  impact, owner, reproduction, root cause, fix/mitigation, and verification.
- Fix the user `report-processor.service` identity configuration and prevent its
  one-minute timer from generating repeated failures or overlapping work.
- Diagnose the failed `tmux-restore.service` and either restore it reliably or
  disable/remove it with documented replacement behavior.
- Make dashboard shutdown bounded and graceful across child mode processes; no
  normal stop may reach systemd's forced-kill timeout.
- Treat client disconnects/BrokenPipe as expected WebUI transport outcomes
  without recursive error writes or traceback noise.
- Diagnose USB device 5 transfer loss (the C-Media/Intel-ID USB audio device),
  triggerhappy hook failures, and audio xruns/buffer starvation across USB,
  HDMI, and Bluetooth.
- Diagnose Wi-Fi scan/driver failures and transient Tailscale DNS/control-plane
  outages; fix local causes and classify external outages with bounded recovery
  and useful health reporting.
- Preserve the now-successful logrotate configuration with a regression check
  for unsafe `/tmp/tui_fresh.log` rotation.
- Coordinate Bluetooth-specific failure fixes with
  `bluetooth-dbus-live-events_20260723` rather than implementing them twice.
- Add focused CEC, terminal, route, EOF, shutdown, service-unit, audio, network,
  and negative-path tests.
- Raise `rpi_dashboard` coverage above 80% with behavior-focused assertions.
- Define reproducible remote Playwright visual baselines on Milhy-PC.

## Optimization Requirements

- Record idle and active CPU per process and per core, especially core 0; RSS,
  proportional memory where available, swap activity, wakeups, I/O, API latency,
  TUI refresh work, PipeWire xruns, and service restart rates.
- Reduce TUI steady-state RSS toward the 20 MiB product target or update the
  target only with an evidence-backed architectural decision and approval.
- Eliminate unnecessary polling, duplicated state refreshes, subprocess calls,
  log storms, timer wakeups, and permanently idle services.
- Tune PipeWire buffers/quantum, resampling, and loopback only after isolating
  USB scheduling, codec/profile, and graph-load causes; retain before/after xrun
  and latency evidence.
- Validate memory pressure over time rather than treating occupied swap alone as
  proof of active thrashing.

## Non-Functional Requirements

- Performance: checks remain practical on CI and avoid browser load on the Pi.
- Reliability: every failure is fixed, safely mitigated, or explicitly classified
  as external/informational with monitoring and recovery evidence.
- Security: secrets and machine-specific runtime state stay out of committed
  artifacts; optimization must not weaken isolation or authentication.
- Safety: hardware-mutating experiments require a narrow procedure and rollback.

## Acceptance Criteria

- [ ] Every entry in `log-audit.md` has a verified resolution or an explicit,
  evidence-backed non-actionable/external disposition; no unknown item remains.
- [ ] `systemctl --failed` and `systemctl --user --failed` contain no unresolved
  project-owned unit; report processing no longer fails every minute.
- [ ] Dashboard stop, WebUI disconnect, tmux restore, logrotate, Wi-Fi/Tailscale,
  triggerhappy, USB transport, and audio xrun regression checks pass.
- [ ] A representative audio soak has no unbounded resync/broken-pipe log storm
  and meets an approved xrun/latency threshold.
- [ ] Measured TUI/ WebUI CPU, memory, wakeup, API latency, and per-core results
  improve or have approved evidence for retaining the baseline.
- [ ] `pytest --cov=rpi_dashboard` reports more than 80% meaningful coverage.
- [ ] Remote Playwright baselines cover desktop, tablet, and mobile.
- [ ] Full repository checks and the completion gate pass.

## Constraints and Dependencies

- Playwright executes remotely from Milhy-PC.
- Bluetooth-owned failures are verified jointly with the Bluetooth track.
- Current log observations cover the current boot/journal retention; a soak and
  fresh-boot verification are required before claiming exhaustive resolution.

## Risks

- Tuning buffers can hide xruns by increasing latency; record both metrics.
- Killing background services can remove recovery features; prove ownership and
  use before disabling anything.
- Broad log matching includes external/transient events; classify them honestly
  instead of forcing unrelated code changes.

## Out of Scope

- Inflating coverage with no-op assertions or running Chromium on the Pi.
- Deleting a service, changing kernel/USB parameters, or clearing swap merely to
  make a metric look clean without root-cause evidence and approval.

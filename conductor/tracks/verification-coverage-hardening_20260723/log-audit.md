# Log Audit: 2026-07-23 Baseline

## Scope

Read-only review of current-boot system/user journals, project services, kernel
Bluetooth/audio/input messages, failed units, USB topology, and a point-in-time
resource sample. Counts reflect retained journal data and may combine repeated
messages; implementation must recapture a fresh-boot and soak baseline.

## Actionable failure ledger

| Class | Evidence observed | Planned disposition |
|---|---|---|
| Report worker | `report-processor.service` failed about 2,806 times with `216/GROUP`; user unit incorrectly contains `User=milhy777` and runs each minute | Fix installed user unit and installer/source alignment, use the project interpreter, prevent overlap/log storms, test one successful timer cycle |
| Tmux restore | `tmux-restore.service` remains failed; older detailed journal rotated | Reproduce safely, validate script/session assumptions, then fix or intentionally retire with tested replacement |
| Dashboard shutdown | `dashboard@milhy777.service` hit SIGTERM timeout/forced kill and signal failure | Define one bounded mode/process-group shutdown owner, graceful deadline, diagnostics, and systemd test |
| WebUI disconnects | Repeated `BrokenPipeError`, including a second error while trying to serialize the first | Treat client disconnect as expected, stop writing after disconnect, add transport tests and rate-limited logging |
| USB audio transport | USB device 5 produced roughly 2,019 FIQ NYET losses and 139 FIQ timeouts; topology identifies the 12 Mbps USB PnP audio/HID device | Correlate power/bus/sample-rate/driver/load with audio errors; change only the smallest verified layer and soak test |
| PipeWire graph | Hundreds of USB/HDMI resyncs, HDMI broken pipes, xruns, and one out-of-buffers event; Bluetooth nodes also xrun | Measure xrun/latency rate per route, isolate graph/profile/USB causes, tune bounded buffers/quantum/resampling, verify latency |
| Bluetooth adapters | `hci0` scan command timeouts/frame reassembly failures and `hci1` security-unavailable events | Owned by Bluetooth track: adapter-specific recovery, capability/error reporting, no global reset, regression tests |
| Bluetooth profiles | A2DP Source busy and HFP/HSP connection refused for PC/phone | Owned by Bluetooth track: negotiated-role matrix, conflict serialization, profile priority, precise unsupported/refused reason |
| Xbox HID/GATT | Report reference, HID information, battery notification errors; rumble init reached 16 seconds; xpadneo taint is informational unless behavior fails | Owned by Bluetooth/input tracks: verify firmware/profile behavior, time-bound readiness, preserve working input; do not hide out-of-tree-module status |
| WirePlumber battery provider | BlueZ experimental battery provider method unavailable | Prefer graceful feature detection/suppression; enable experimental BlueZ only through separate approved evidence gate |
| Triggerhappy hotplug | `th-cmd` hook failures for Xbox/input event nodes | Inspect hotplug command/permissions and eliminate failures without multiple readers or exclusive grabs |
| Wi-Fi | brcmfmac scan failure/timeout and one `CTRL-EVENT-SCAN-FAILED` | Reproduce through dashboard Network flow, distinguish busy scan from driver/network loss, bounded retry and visible health |
| Tailscale/DNS | DNS refusal, coordination/DERP timeouts, log upload failures; service is currently connected | Verify local DNS/routing, classify remote outage, add bounded health/recovery display without restart loops |
| Logrotate | Prior `/tmp/tui_fresh.log` insecure-parent failure; latest two runs succeeded | Preserve the current fix with configuration validation and regression check; no active repair unless it recurs |

## Resource findings

- RAM sample: 503 MiB used of 731 MiB, 227 MiB available.
- Swap sample: 255 MiB of 255 MiB occupied; measure swap-in/out over time before
  calling it active thrashing or clearing it.
- Live `tui.py`: about 59.5 MiB RSS and 7.5% CPU at the sample, above the
  documented 20 MiB core TUI memory target.
- PipeWire: about 8 MiB RSS and 5.7% CPU while the audio graph was producing
  repeated resync messages.
- Webserver: about 23 MiB RSS at low CPU.
- Tailscale: about 64.5 MiB RSS; external service behavior must be optimized only
  through supported configuration and after measuring project impact.
- Core 0 hosts several background/input tasks; per-core sampling must accompany
  Bluetooth/audio and global shortcut work.

## Classification rules

- A log class closes only with a verified fix, safe mitigation, or explicit
  external/informational disposition backed by current evidence.
- Repeated messages are one failure class plus a rate/log-storm issue, not
  thousands of independent bugs.
- Kernel, firmware, USB power, BlueZ experimental, and system-wide audio changes
  require a rollback plan and explicit approval before mutation.

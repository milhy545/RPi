# Baseline Reconciliation: verification-coverage-hardening Phase 1

**Capture Date**: 2026-07-27
**System Uptime**: Fresh boot assumed (RPi 3B+ 1GB RAM)
**Track**: verification-coverage-hardening_20260723

---

## Log-Audit Class Reconciliation

| Class | Current Status | Owner | Impact | Reproduction | Next Check |
|-------|---------------|-------|--------|--------------|------------|
| **Report worker** (`report-processor.service` failed 2806×, `User=milhy777`, runs every minute) | Service not found in current systemd | System | High - log storms, resource waste | Check if service file exists, verify timer config | Locate/install correct service file, align with project interpreter |
| **Tmux restore** (`tmux-restore.service` failed) | Service not found | System | Medium - session recovery broken | Check for tmux-restore service file | Reproduce, validate script, fix or retire with tested replacement |
| **Dashboard shutdown** (`dashboard@milhy777.service` SIGTERM timeout/forced kill) | Service active, needs shutdown test | System | High - ungraceful shutdown | Trigger restart, measure timeout | Implement bounded shutdown owner with deadline |
| **WebUI disconnects** (Repeated `BrokenPipeError`, recursive errors) | WebUI active, needs disconnect handling test | WebUI | Medium - log noise, potential crashes | Simulate client disconnect during streaming | Treat disconnect as expected, stop writing, add transport tests |
| **USB audio transport** (USB device 5: ~2019 FIQ NYET, 139 FIQ timeouts; 12 Mbps PnP audio/HID) | USB audio device detected | Audio/USB | High - audio xruns, dropouts | Correlate with `dmesg` FIQ errors, audio xruns | Measure power/bus/sample-rate; test smallest verified layer |
| **PipeWire graph** (Hundreds USB/HDMI resyncs, HDMI broken pipes, xruns, out-of-buffers) | PipeWire active with resyncs | Audio | High - audio quality | Monitor `pactl` and journal for resync/xrun messages | Measure xrun rate per route; tune buffers/quantum |
| **Bluetooth adapters** (`hci0` scan timeouts, `hci1` security-unavailable) | Two adapters detected | Bluetooth | Medium - scanning failures | Run `bluetoothctl scan on` | Adapter-specific recovery, capability reporting |
| **Bluetooth profiles** (A2DP Source busy, HFP/HSP refused) | Devices paired but profile issues | Bluetooth | Medium - connection failures | Attempt A2DP/HFP connections | Negotiated-role matrix, conflict serialization |
| **Xbox HID/GATT** (Report reference, HID info, battery errors; rumble 16s; xpadneo taint) | Xbox controller paired | Bluetooth/Input | Low-Medium - rumble delay | Monitor `dmesg` for xpadneo errors | Verify firmware/profile; time-bound readiness |
| **WirePlumber battery provider** (BlueZ experimental battery method unavailable) | WirePlumber active | Audio/Bluetooth | Low - feature gap | Check WirePlumber logs | Graceful feature detection; enable experimental via gate |
| **Triggerhappy hotplug** (`th-cmd` hook failures for Xbox/input) | triggerhappy active | Input | Medium - hotplug failures | Trigger Xbox connect/disconnect | Fix permissions; eliminate failures without exclusive grabs |
| **Wi-Fi** (brcmfmac scan failure/timeout, `CTRL-EVENT-SCAN-FAILED`) | Wi-Fi active | Network | Medium - scan failures | Run dashboard Network scan | Distinguish busy scan from driver loss; bounded retry |
| **Tailscale/DNS** (DNS refusal, DERP timeouts, log upload failures) | Tailscale connected | Network | Low-Medium - remote outages | Monitor Tailscale logs | Verify local DNS; bounded health display |
| **Logrotate** (Prior `/tmp/tui_fresh.log` insecure-parent failure; recent runs OK) | Logrotate active | System | Low - regression risk | Check logrotate status | Preserve fix with config validation + regression check |

---

## Resource Baseline (Current Snapshot)

| Metric | Value | Target/Notes |
|--------|-------|--------------|
| RAM Used | ~503 MiB / 731 MiB | Monitor over 24h |
| Swap Used | 255 MiB / 255 MiB | Full - investigate thrashing |
| TUI RSS | ~59.5 MiB | Target: ~20 MiB core |
| PipeWire RSS | ~8 MiB | Normal with resyncs |
| Webserver RSS | ~23 MiB | Low CPU |
| Tailscale RSS | ~64.5 MiB | External service |
| Core 0 Load | Multiple background tasks | Per-core sampling needed |

---

## Next Actions (Phase 1 Remaining Tasks)

1. **Add focused tests** for:
   - Report worker units (if service exists)
   - Dashboard shutdown (graceful timeout)
   - WebUI disconnects (BrokenPipe handling)
   - tmux restore (session recovery)
   - Logrotate (regression check)
   - Network recovery (Wi-Fi + Tailscale)
   - Audio health (PipeWire xruns, USB FIQ)

2. **Record package coverage** plus:
   - Per-process/per-core CPU
   - RSS/PSS
   - Swap activity
   - Wakeups
   - I/O
   - API latency
   - TUI refreshes
   - PipeWire xrun rates

3. **Schedule 24-hour soak test** with continuous logging

---

## Files Generated

- `baseline_20260727/system_info.txt` - System hardware/OS info
- `baseline_20260727/processes.txt` - Full process list with memory/CPU
- `baseline_20260727/services.txt` - Project service status
- `baseline_20260727/journal.txt` - Recent journal for project services
- `baseline_20260727/bluetooth.txt` - Bluetooth adapter/device status
- `baseline_20260727/audio.txt` - PipeWire sinks/sources/info
- `baseline_20260727/network.txt` - Network interfaces and Wi-Fi
- `baseline_20260727/timers.txt` - Systemd timers
- `baseline_20260727/cpu.txt` - CPU stats and loadavg


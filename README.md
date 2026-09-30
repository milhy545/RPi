# Raspberry Pi Dumb TV & Living-Room Appliance

[![Platform: Raspberry Pi OS](https://img.shields.io/badge/Platform-Raspberry%20Pi%203%20Model%20B-red.svg)](https://www.raspberrypi.com/)
[![Kernel: Linux](https://img.shields.io/badge/Kernel-Linux%20Affinity%20Tuning-orange.svg)](https://www.kernel.org/)
[![UI: Textual TUI](https://img.shields.io/badge/UI-Textual%20TUI-blue.svg)](https://github.com/Textualize/textual)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)  
[🇨🇿 Kompletní česká verze dokumentace zde](./README.cz.md)

A low-RAM, embedded Raspberry Pi living-room dashboard and media appliance engineered to push constrained hardware to its absolute limit through **deterministic CPU core affinity and hardware IRQ isolation**.

Features zero-overhead switching between a Textual dashboard, fullscreen 1080p MPV playback, and Steam Link streaming from the main workstation.

---

## 🔬 Systems Engineering Deep-Dive: Overcoming Silicon Limits

Pushing reliable 1080p video playback and low-latency Bluetooth audio on a Raspberry Pi 3 Model B (BCM2837 SoC, 1GB RAM) exposed critical architectural bottlenecks in standard Linux scheduling.

### 1. Thermal Saturation: Core Packing vs. Core Spreading
- **The Failure Mode:** Standard Linux CFS (Completely Fair Scheduler) spreads background load evenly across all 4 cores. This distributive model keeps all cores continuously awake, preventing them from entering deep low-power sleep states (C-states). The resulting static leakage current rapidly overheated the SoC past 80–85°C, triggering aggressive hardware thermal throttling down to **600 MHz**, where hardware-accelerated video decoding (`v4l2m2m-copy`) collapsed completely with severe frame drops.
- **The Core Packing Strategy:** By strictly packing the video workload exclusively onto **Cores 1 & 2** via `taskset -c 1,2`, L1 cache hit rates are maximized, L2 cache thrashing across the shared 512 KiB L2 cache is eliminated, and idle cores retain thermal headroom.

### 2. Wi-Fi & Bluetooth Antenna Contention (The Cypress Coexistence Defect)
- The Raspberry Pi 3 shares a single Cypress wireless chip and physical antenna for both 2.4 GHz Wi-Fi and Bluetooth. Time-division multiplexing caused audio packets to stutter whenever network downloads occurred.
- In MPV, audio acts as the Master Reference Clock (`video-sync=audio`). Any audio buffer underrun (*xrun*) causes MPV to aggressively drop video frames.

### 3. The 4-Core CPU Affinity Matrix
To guarantee rock-solid stability without thermal collapse, a deterministic core affinity model was implemented:

| Core | Dedicated Assignment | Engineering Rationale |
| :--- | :--- | :--- |
| **Core 0** | **Housekeeping & IRQ Shield** | Absorbs all hardware interrupts (USB, Wi-Fi, Ethernet, SD card) and background daemons (`NetworkManager`, `tailscaled`, `Textual TUI`). |
| **Cores 1 & 2** | **Golden Video Engine** | MPV player main thread and `v4l2m2m-copy` decode threads hard-pinned via `taskset -c 1,2`. |
| **Core 3** | **Real-Time Audio & Emergency Swing** | Reserved for PipeWire / WirePlumber with guaranteed real-time priority (`rtprio 95` configured via `/etc/security/limits.d/25-pw-rlimits.conf` bypassing RTKit). Core 3 sleeps in low-power state, standing by to assist Cores 1 & 2 if video load exceeds 160% for >3 seconds. |

---

## 🛠️ Project Structure & Existing Documentation

- `main.py` — Minimal entry point
- `tui.py` — Textual TUI dashboard
- `webserver.py` — WebUI, REST API, and terminal WebSocket server (port 8099)
- `mode_switcher.py` — Foreground application supervisor
- `keys2mpv.py` — Multimedia keyboard daemon
- [Full Documentation Index](./docs/README.md)
- [Project Overview](./docs/overview.md)
- [WebUI & API Reference](./docs/webserver-8099.md)
- [Textual Dashboard Reference](./docs/tui.md)
- [Mode Switcher Reference](./docs/mode-switcher.md)
- [Multimedia Keyboard Daemon](./docs/keys2mpv.md)
- [Testing & Verification Guide](./docs/testing.md)
- [Operational Playbooks](./docs/operations.md)

# Product Guide: RPi Dumb TV Dashboard

## 1. Product Vision
The RPi Dumb TV Dashboard is a highly optimized, Terminal User Interface (TUI) serving as the central hub for a low-RAM (731 MiB) Raspberry Pi 3 Model B connected to a living room TV. Operating entirely without a heavy desktop environment or Kodi, it embraces the "Goat Principle" (Functionality > Aesthetics) while maintaining a sleek, hacker-style "Matrix" aesthetic when idle. Its primary purpose is to be an invisible, zero-latency launcher for media and game streaming.

## 2. Target Audience
- **Primary User:** Power users and home-lab enthusiasts (Milhy) managing their local ecosystem.
- **Secondary Users:** Household members or guests casting YouTube or playing games without needing technical knowledge.

## 3. Core Features (COMPLETED)

### 3.1 Zero-Overhead Mode Switching
- **Game Streaming:** Launches `steamlink` or `moonlight` for low-latency gaming. **GeForce Now** is streamed via Moonlight from a local host PC running Sunshine to bypass the RPi 3B's browser limitations.
- **Media & Music Streamers:** Launches `mpv` (with `yt-dlp`) for zero-ad YouTube playback, runs `WPE WebKit` for Spotify Free, monitors the background **Spotify Connect** daemon (`raspotify`), and supports **Amazon Music Kiosk** (via local audio-only Chromium kiosk mode) and DLNA casting.

### 3.2 WebUI (Port 8099) - "GFN-TV"
- **YouTube Playback:** `yt-dlp` + `mpv` via IPC socket (`/tmp/rpi-mpv.sock`)
- **Seek Bar:** Absolute seek via `/mpv/seekabs?pos=N` endpoint + HTML5 range input
- **Keyboard Controls:** Arrow keys (seek ±10s), f/g/h (25/50/75%), multimedia keys
- **YouTube Cookies:** CDP extraction from BrowserOS on Milhy-PC (61 cookies, age-restricted videos work)
- **Terminal Tab:** WebSocket (port 8098) → tmux session `RPi:1` with diff polling

### 3.3 CEC Control (via cec-ctl)
- **Power:** On (IMAGE_VIEW_ON) / Off (STANDBY)
- **Navigation:** Up/Down/Left/Right/Select/Back/Menu/CH+/CH-
- **Volume:** Up/Down/Mute
- **Input Switching:** Active Source (HDMI 1/2/3)
- **Remote→MPV Bridge:** cec-client daemon maps TV remote keys to mpv IPC commands

### 3.4 Audio Management
- **Bluetooth:** Samsung Soundbar J-Series paired, A2DP sink
- **HDMI:** Native RPi HDMI audio
- **DLNA Scan:** `gssdp-discover` finds 2 MediaRenderers (LG TV + WiiMu)
- **USB Audio Loopback:** C-Media USB sound card input (Alexa AUX) → BT Soundbar via PipeWire module-loopback

### 3.5 System Telemetry
- Real-time monitoring: CPU usage, RAM allocation, CPU temperature
- CPU affinity pinning: mpv→cores 0-1, rest→cores 2-3 (cpuset-priorities.sh + systemd)
- RAM limit: mpv ≤ 500 MiB, core TUI ≤ 20 MiB

### 3.6 Network Listener (Port 8090)
- Cast commands from mobile devices
- API Key authorization, CORS support

## 4. Key Constraints
- **Memory Limit:** Core TUI < 20MB RAM, mpv < 500 MiB (total 731 MiB)
- **CPU Pinning:** mpv→cores 0-1, rest→cores 2-3 (dynamic via cpuset-monitor when mpv playing)
- **No Desktop Environment:** Headless, no X11/Wayland compositor
- **No Bluetooth Audio Sink:** RPi does not receive BT audio (soundbar is the sink)
- **Pre-Install Research:** Before ANY install, research aarch64 compat, Debian 12, RAM/disk footprint

## 5. Hardware Verified
- **RPi:** 3 Model B Rev 1.2, 4× Cortex-A53 @ 1200 MHz, 731 MiB RAM
- **OS:** Debian 12 (bookworm), kernel 6.12.87+rpt-rpi-v8
- **USB Audio:** C-Media PnP Sound Device (input/output), XING WEI 2.4G (remote input)
- **Bluetooth:** Samsung Soundbar J-Series (24:4B:03:92:0B:8C)
- **Network:** Tailscale, Wi-Fi hotspot (RPi-service)

## 6. Key Files
- `~/rpi-dashboard/webserver_8099.py` - HTTP (8099) + WebSocket (8098) server
- `~/rpi-dashboard/keys2mpv.py` - Multimedia keyboard daemon
- `~/rpi-dashboard/tui.py` - Textual TUI with mode switcher
- `~/rpi-dashboard/yt-cookies.txt` - YouTube cookies from BrowserOS
- `~/rpi-dashboard/cpuset-priorities.sh` - CPU affinity setup
- `~/.tmux.conf` - tmux with resurrect+continuum persistence
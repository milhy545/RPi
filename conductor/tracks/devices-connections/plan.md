# Implementation Plan: Devices & Connections Management (Production-Grade)

This track implements the "Devices & Connections" management panel within the TUI dashboard, integrates remote system audio (HDMI, Bluetooth, DLNA), Wi-Fi Hotspot controls, Raspotify monitoring, and expands the Cast API server to support remote status, control, and administration.

## Phase 1: TUI Tabbed Navigation & Stream Modes (GeForce Now & Amazon Music)
- [x] Task: Integrate `TabbedContent` and `TabPane` into `RPiDashboard` in `tui.py`.
- [x] Task: Split the dashboard into two main tabs:
  - **"Control & Telemetry"**: Current dashboard layout (buttons, system statistics, log output).
  - **"Devices & Settings"**: New settings layout with nested containers for managing audio, bluetooth, wifi, and tailscale.
- [x] Task: Add a new sidebar button for launching **"GeForce Now"** via **Moonlight** (pointing to a local host PC running Sunshine and GFN to bypass the RPi 3B's browser performance limitations).
- [x] Task: Add a new sidebar button for launching **"Amazon Music Kiosk"** (running Chromium locally in kiosk mode targeting `https://music.amazon.com` — since it is audio-only, the RPi 3B can decode it without performance issues).
- [x] Task: Create a dedicated directory `/home/milhy777/rpi-dashboard/streaming_setup/` containing:
  - `README.md` - Důkladná a precizní dokumentace k nastavení Sunshine na hostujícím PC (Milhy-PC), popisu párovacího toku (4-místný PIN v Web UI) a spuštění GFN.
  - `install-sunshine-mx.sh` - One-click setup skript pro instalaci a spuštění Sunshine na **Milhy-PC** (pro MX Linux 25 KDE/Debian). Skript bude automaticky detekovat GPU topologii (Intel iGPU + NVIDIA dGPU) a vygeneruje konfiguraci `sunshine.conf` s popisem a možností volby enkodéru (Intel QuickSync/VAAPI přes `/dev/dri/renderD128` vs NVIDIA NVENC) pro flexibilitu workflow (uvolnění dGPU pro AI zátěž).
  - `install-moonlight.sh` - One-click setup skript pro instalaci a konfiguraci Moonlight klienta na RPi 3B.

## Phase 2: Network & Tailscale Info Panel
- [x] Task: Implement backend parsing for `tailscale status` (to get node name, IP, Tailscale status, online peer count) and local interface IPs.
- [x] Task: Design and implement a real-time read-only status panel in the TUI under the settings tab.

## Phase 3: Audio Output Selection Panel (HDMI, Bluetooth, DLNA)
- [x] Task: Implement parser for `pactl list short sinks` and `pactl get-default-sink` using Python `subprocess`.
- [x] Task: Group and label detected sinks clearly:
  - **HDMI**: `alsa_output.platform-...`
  - **Bluetooth**: `bluez_sink....`
  - **DLNA**: Null sinks created dynamically by `pa-dlna` (e.g., `LG_TV-...`, which redirects audio to the TV/renderers).
- [x] Task: Build an interactive selection list in the TUI to select the default audio sink.
- [x] Task: Add a status indicator and control to restart/toggle the `pa-dlna` background process.
- [x] Task: Wire selection changes to run `pactl set-default-sink <sink_id>` and refresh the default sink display.

## Phase 4: Bluetooth Pairing & Management Panel
- [x] Task: Implement python wrapper for `bluetoothctl` command execution (listing paired devices, scanning, pairing, connecting, disconnecting, removing).
- [x] Task: Create interactive Bluetooth panel with:
  - List of paired devices with Connect/Disconnect/Unpair actions (utilizing `bluetoothctl devices Paired`).
  - "Scan for Devices" button (runs `bluetoothctl scan on` for 5s asynchronously).
  - List of discovered/unpaired devices with Pair/Connect actions.

## Phase 5: Wi-Fi Access Point & Hotspot Configuration
- [x] Task: Read active hidden hotspot details (`SSID: RPi-service`) by parsing `/etc/hostapd/rpi-service.conf`.
- [x] Task: Implement a parser for `/var/lib/misc/dnsmasq.leases` to display a list of connected clients on the rescue hotspot.
- [x] Task: Add settings control (both in TUI and via API) to toggle the rescue hotspot (`systemctl start/stop hostapd dnsmasq`).
- [x] Task: Implement a fallback Wi-Fi scanner and client connection flow using `nmcli` for cases where the hotspot is disabled.

## Phase 6: Spotify Connect & Production-Grade API Routes
- [x] Task: Monitor the status of the background Spotify Connect client (`raspotify.service`) and allow starting/stopping it.
- [x] Task: Refactor API server in `tui.py` to allow concurrent requests while a mode is running (remove global `api_server_paused` block).
- [x] Task: Implement selective request rejection: return `409 Conflict` only for `/play` requests if a mode is already running.
- [x] Task: Implement the following routes:
  - **`GET /status`**: Returns JSON with active mode, system resources, screensaver state, current media details, and network info.
  - **`POST /player/pause`**: Toggles pause on the running `mpv` process.
  - **`POST /player/stop`**: Terminates the active subprocess cleanly.
  - **`POST /player/volume`**: Changes volume via `pactl` (`{"level": 0-100}`).
  - **`POST /player/seek`**: Seeks forward/backward in the current media (`{"seconds": N}`).
  - **`GET /audio/sinks`** & **`POST /audio/sinks/select`**: Remote audio sink control.
  - **`GET /bluetooth/devices`** & **`POST /bluetooth/connect`**: Remote Bluetooth administration.
  - **`GET /wifi/networks`** & **`POST /wifi/connect`**: Remote Wi-Fi selection.
  - **`POST /system/reboot`**: Reboots the system.
  - **`POST /system/screensaver`**: Remotely wakes/triggers the Matrix screensaver.
- [x] Task: Add CORS (Cross-Origin Resource Sharing) support to allow browser-based remote controllers.
- [x] Task: Add API Key authorization (`X-API-Key` header validation) configured via the `.env` file.

## Phase 7: Validation & Verification
- [x] Task: Write automated integration tests (e.g., `test_production_api.py`) verifying all new API routes and the selective concurrency guard.
- [x] Task: Perform manual validation on QEMU / ARM chroot for network, audio, and Bluetooth commands.
- [x] Task: Conductor - User Manual Verification 'Devices & Connections' (Protocol in workflow.md).

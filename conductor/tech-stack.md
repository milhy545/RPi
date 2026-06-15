# Tech Stack: RPi Dumb TV Dashboard

## 1. Runtime Environment

| Parameter | Value |
|---|---|
| **Target HW** | Raspberry Pi 3 Model B Rev 1.2, 4× Cortex-A53 @ 1200 MHz, 731 MiB RAM |
| **OS** | Debian 12 (bookworm), kernel 6.12.87+rpt-rpi-v8 |
| **Python** | ≥ 3.12 (uv venv) |
| **Package Manager** | `uv` (strictly no pip/pipx globally) |
| **Process Manager** | systemd (autostart dashboard, keys2mpv, cpuset) |

## 2. Core Dependencies

| Package | Purpose | Note |
|---|---|---|
| `textual` ≥ 8.2.7 | TUI framework | Main UI layer |
| `psutil` | System telemetry | CPU, RAM, temp |
| `aiohttp` | HTTP server + client | Network listener (port 8099), yt-dlp |
| `websockets` | WebSocket server | Terminal tab (port 8098) |
| `yt-dlp` | YouTube stream resolver | uv tool / venv, v2026.06.09 |
| `yt-dlp` cookies | BrowserOS CDP extraction | 61 cookies, age-restricted OK |

## 3. External Tools (System-level)

| Tool | Purpose | Install |
|---|---|---|
| `mpv` | Video player | `apt install mpv` |
| `yt-dlp` | YouTube resolver | `uv tool install yt-dlp` |
| `steamlink` | Game streaming client | Flatpak / ARM binary |
| `wpe-webkit` / `cog` | Spotify kiosk | `apt` / custom build |
| `bluetoothctl` | BT pairing | BlueZ |
| `cec-ctl` | CEC control | `apt install cec-utils` |
| `cec-client` | CEC bridge daemon | `apt install cec-utils` |
| `gssdp-discover` | DLNA scan | `apt install gupnp-tools` |
| `pactl` / `pw-cli` | PipeWire audio control | `apt install pipewire` |
| `nala` | APT frontend | `apt install nala` |
| `tmux` | Terminal multiplexer | `apt install tmux` |
| `cpuset` | CPU affinity | `apt install cpuset` |

## 4. Development Tools

| Tool | Purpose |
|---|---|
| `uv` | Dependency management, virtualenv, task runner |
| `ruff` | Linting + formatting (replaces flake8/black) |
| `pytest` | Unit tests |
| `textual-dev` | TUI dev tools (console, screenshot) |

## 5. Architecture Decisions

### 5.1 Why Textual?
- Native terminal support — no X11/Wayland overhead
- Reactive framework with CSS-like styling
- Async-first — integrates naturally with `aiohttp` network listener
- Low memory footprint (< 20MB for TUI)

### 5.2 Why aiohttp over FastAPI/Flask?
- Lightweight — no Pydantic/Starlette overhead
- Native async — shares event loop with Textual
- Client and server in one package

### 5.3 Why mpv + yt-dlp?
- Zero-ad YouTube playback (vs browser)
- Hardware decoding via v4l2m2m (v4l2m2m hwdec)
- IPC socket control (`--input-ipc-server`)
- `--keep-open=always` prevents socket freeze on video end

### 5.4 CPU Affinity Strategy
- **Static:** `cpuset-priorities.sh` at boot (mpv→0-1, rest→2-3)
- **Dynamic:** `cpuset-monitor.sh` (disabled — bug: pins mpv to wrong cores on start)
- **Rationale:** mpv is ALWAYS highest priority, never competes for CPU/RAM

### 5.5 Audio Architecture
- **PipeWire** for all audio routing
- **Bluetooth A2DP sink** (Samsung Soundbar)
- **HDMI** native RPi audio
- **DLNA** via `gssdp-discover` (scan works, rendering needs UPnP renderer)
- **USB Loopback:** `module-loopback` (USB input mono → BT sink stereo, 48kHz, 20ms latency)

### 5.6 YouTube Cookies Pipeline
1. **BrowserOS on Milhy-PC** — user logged into YouTube
2. **CDP port 9108** — `--remote-allow-origins=*` enabled
3. **WebSocket** → `Network.getAllCookies` → 61 cookies (incl. httpOnly)
4. **Netscape format** → `~/rpi-dashboard/yt-cookies.txt`
5. **yt-dlp** `cookiefile` parameter → age-restricted videos work

### 5.7 CEC Architecture
- **cec-ctl** for command sending (reliable, low-level)
- **cec-client** for bridge daemon (listens for TV remote events)
- **Bridge maps:** Play/Pause/Stop/Seek/Vol/Mute → mpv IPC
- **Power On fix:** `--image-view-on` (not `--text-view-on`)

### 5.8 Terminal Tab
- **WebSocket** port 8098 (separate from HTTP 8099)
- **tmux session `RPi:1`** — dedicated shell window
- **Diff polling:** `capture-pane -S -{height}` every 500ms
- **xterm.js** in browser via CDN

### 5.9 Rejected Alternatives
| Technology | Reason |
|---|---|
| Kodi | Bloatware, 200+ MB RAM |
| Electron/web UI | 150+ MB RAM, requires Chromium |
| Flask/FastAPI | Heavier than aiohttp |
| curses (raw) | Too low-level, Textual better DX |
| pulseaudio-dlna | Not in Debian 12/backports |
| rygel | Not in Debian 12/backports |
| Playwright headless | Too heavy for 731 MiB |

## 6. Key Paths
- `~/rpi-dashboard/` — main project
- `~/.pi/RULES.md`, `~/.pi/agent/rules.md` — core rules
- `~/.pi/PERSONA.md` — agent persona
- `~/.tmux.conf` — tmux with resurrect+continuum
- `~/rpi-dashboard/yt-cookies.txt` — YouTube cookies
- `/tmp/rpi-mpv.sock` — mpv IPC socket
- `/dev/input/event2` — multimedia keyboard (XING WEI 2.4G)
# RPi Dumb TV Dashboard — Architectural Summary & Bottleneck Analysis

**Generated:** 2026-06-06  
**Target Hardware:** Raspberry Pi (1 GB RAM, ARMv7/ARM64, headless)  
**OS:** Raspberry Pi OS Lite (Debian-based, no desktop environment)

---

## 1. Project Overview

The RPi Dumb TV Dashboard is a minimalist TUI-based controller designed to replace Kodi on a 1 GB Raspberry Pi connected to a living-room TV. It provides zero-overhead mode switching between game streaming (SteamLink, Moonlight/GeForce Now), media playback (MPV/yt-dlp), music streaming (Spotify via WPE WebKit, Amazon Music kiosk, Spotify Connect daemon, DLNA), and system monitoring — all without a desktop environment, X11, or Electron.

The project is implemented as a Python 3.12+ application using the **Textual** TUI framework, **aiohttp** for a local REST API listener (port 8090), and shell-based provisioning scripts.

---

## 2. Codebase Architecture

### 2.1 Entry Point & Module Map

```
main.py                          # Minimal CLI stub — prints "Hello from rpi!"
                                 # Not used in production; tui.py is the real entry point.
tui.py          (~1106 lines)    # Core application: TUI dashboard, API server, mode logic
mode_switcher.py (~206 lines)    # Process lifecycle manager: suspend/resume TUI, spawn subprocesses

provisioning/
├── provision.sh                 # Master orchestrator — runs steps 1–5 in order
├── 01-install-apt-deps.sh       # System APT packages (mpv, python3, git, build-essential, etc.)
├── 02-install-uv-ytdlp.sh       # uv (Python PM) + yt-dlp standalone binary
├── 03-clone-repo.sh             # Git clone or pull of the repo
├── 04-setup-venv.sh             # uv sync (creates venv, installs deps)
├── 05-install-service.sh        # systemd service install & enable
├── dashboard.service            # systemd unit template (%i = username)
└── README.md                    # Script documentation
```

**Entry-point chain (production):**  
`systemd → dashboard.service → .venv/bin/python tui.py → RPiDashboard.app.run()`

**Entry-point chain (headless/test):**  
`python tui.py --headless → aiohttp server only (no TUI)`

### 2.2 Layer Architecture

```
┌──────────────────────────────────────────────────────┐
│                   TUI Layer (Textual)                 │
│  RPiDashboard(App)                                   │
│   ├── SystemStats (CPU, RAM, temp, IP polling 2s)    │
│   ├── ModeStatus (reactive mode label)               │
│   ├── Log (syslog widget, 200-line ring buffer)      │
│   ├── TabbedContent (Control, Settings)              │
│   ├── IdleScreen / MatrixRain (screensaver)          │
│   └── Button-triggered mode switching                │
├──────────────────────────────────────────────────────┤
│              API Layer (aiohttp, port 8090)           │
│  13 routes: play, status, player/*, audio/*,          │
│  bluetooth/*, wifi/*, system/reboot, system/scrsaver  │
│  Middleware: CORS, optional API key auth              │
├──────────────────────────────────────────────────────┤
│           Mode Switcher Engine (mode_switcher.py)      │
│  ┌─ State Machine: IDLE→SUSPENDING→RUNNING→RESUMING  │
│  ├─ Process lifecycle: subprocess.Popen + watchdog    │
│  ├─ Textual suspend() / resume() context manager      │
│  ├─ Concurrency guard (asyncio.Lock + state check)    │
│  ├─ LogBuffer (200-line in-memory ring buffer)        │
│  └─ Signal handlers (SIGTERM, SIGINT)                │
├──────────────────────────────────────────────────────┤
│          External Processes  (spawned on demand)      │
│  steamlink | moonlight | mpv | wpe | chromium --kiosk │
└──────────────────────────────────────────────────────┘
```

### 2.3 Component Breakdown

#### 2.3.1 `tui.py` — Main Application

| Component | Type | Responsibility | Memory Profile |
|---|---|---|---|
| `RPiDashboard` | `textual.App` | Root app, layout, routing, compose | ~8–12 MB (Textual runtime + widget tree) |
| `SystemStats` | `textual.Widget` | Polls `/proc/stat`, `/proc/meminfo`, `/sys/class/thermal` every 2s | ~0.5 MB (stateless, string update) |
| `ModeStatus` | `textual.Widget` | Displays current mode label (reactive attribute) | ~0.1 MB |
| `Log` widget | Built-in Textual | Wraps `LogBuffer` — survives suspend/resume via `replay_log_buffer()` | ~0.2 MB (200 lines × ~200 chars) |
| `MatrixRain` | `textual.Widget` | Matrix screensaver — per-frame string generation, 350ms tick | ~0.5–2 MB (full-screen text buffer depends on terminal size) |
| `IdleScreen` | `textual.Screen` | Full-screen overlay, dismiss on key/click | ~0.1 MB (frame + child MatrixRain) |
| API handlers | 13 async methods | JSON REST endpoints, shell subprocess calls | ~3–5 MB (aiohttp event loop + connections) |

**Polling intervals & timers:**
- `SystemStats`: every 2.0 seconds
- `update_settings_data`: every 5.0 seconds
- `MatrixRain.tick`: every 0.35 seconds
- `check_inactivity`: every 1.0 second

#### 2.3.2 `mode_switcher.py` — Process Lifecycle Manager

| Component | Type | Responsibility |
|---|---|---|
| `ModeSwitcher` | Class | State machine, process spawn, signal handling |
| `ModeSwitcherState` | Enum | `IDLE → SUSPENDING → RUNNING → RESUMING → IDLE` |
| `LogBuffer` | Class | 200-line ring buffer for log persistence across suspend/resume |
| `Watchdog` | Coroutine | Timeout-based process termination (used for `TEST_TIMEOUT=30s`) |

**Key design decisions:**
- **Process isolation:** External apps run as separate OS processes, never in-process. Dashboard fully suspends while active mode runs.
- **State machine guards:** `launch()` rejects if `lock.locked()` or `state != IDLE` — prevents double-launch.
- **Graceful fallback:** If `app.suspend()` fails (headless environment), runs without suspension.
- **Signal safety:** `SIGTERM` during `RUNNING` → teardown process then exit; `SIGINT` → teardown only.

#### 2.3.3 `provisioning/` — Deployment Automation

All scripts are **idempotent** (safe to re-run):

| Script | Action | Idempotency Check |
|---|---|---|
| `01-install-apt-deps.sh` | `apt-get install` of 11 packages | `apt-get install -y` is natively idempotent |
| `02-install-uv-ytdlp.sh` | uv installer + yt-dlp binary | `command -v uv` and `command -v yt-dlp` |
| `03-clone-repo.sh` | `git clone` or `git pull --ff-only` | Checks for `.git` directory |
| `04-setup-venv.sh` | `uv sync` | `uv sync` is natively incremental |
| `05-install-service.sh` | systemd unit copy + enable + start | Checks `is-active` before restart |

**Provisioning weakness:** `03-clone-repo.sh` defaults to `$HOME/rpi-dashboard`, but `dashboard.service` hardcodes `WorkingDirectory=/home/%i/rpi-dashboard`. If `INSTALL_DIR` is overridden, service will break. No validation that paths align.

#### 2.3.4 `dashboard.service` — systemd Unit

```ini
Conflicts=getty@tty1.service     # Takes over tty1
ExecStart=.../.venv/bin/python tui.py
StandardInput=tty-force
TTYPath=/dev/tty1
```

**Notable:** The `Conflicts=getty@tty1.service` ensures the dashboard takes over the physical console. The service runs as `%i` (username), with `WorkingDirectory` hardcoded to `/home/%i/rpi-dashboard`.

---

## 3. Data Flow

### 3.1 Mode Switch Flow (e.g., MPV playback)

```
User presses "Spustit MPV" → on_button_pressed()
  → launch_mode("MPV", ["mpv", ...], timeout=MPV_TIMEOUT)
    → mode_switcher.launch(["mpv", "--fs", ..., url])
      → [state: IDLE → SUSPENDING]
        → app.pause_api_server()         # Block incoming API requests
        → app.suspend()                   # Textual: stop rendering, release TTY
        → [state: SUSPENDING → RUNNING]
          → subprocess.Popen(command, stdin=sys.__stdin__, ...)  # Spawn on TTY
          → process.wait()                # Block until MPV exits
        → [state: RUNNING → RESUMING]
          → app.resume_api_server()       # Re-allow API requests
→ mode_status = "IDLE (Dashboard)"
  → app.replay_log_buffer()              # Restore logs from LogBuffer
  → reset_inactivity()                   # Prevent immediate screensaver
```

### 3.2 API Request Flow (e.g., `/play` from mobile)

```
POST /play {"url": "https://youtube.com/watch?v=..."}
  → handle_play()
    → Check mode_switcher.state == IDLE     # Reject 409 if busy
    → play_media(url)
      → mode_status = "MPV (Přehrávač)"
      → mode_switcher.launch(["mpv", ..., url])
        → [same as 3.1 above]
```

### 3.3 Settings Polling Flow (every 5s)

```
update_settings_data()
  → update_network_info()     # ip -br addr, tailscale ip -4
  → update_audio_sinks()      # pactl list short sinks
  → update_bluetooth_devices() # bluetoothctl devices Paired
  → update_wifi_hotspot_info() # cat /etc/hostapd/..., systemctl is-active
```

Each invokes `run_sys_cmd()` → `asyncio.create_subprocess_shell()` → `communicate()` → parse stdout. No caching — every 5 seconds all 4+ shell subprocesses are created.

---

## 4. Memory Budget Analysis

### 4.1 Current Estimated Footprint

| Component | Estimated RAM | Basis |
|---|---|---|
| Python interpreter (CPython 3.12) | ~5–8 MB | Base interpreter on Linux ARM |
| Textual runtime + widget tree | ~8–12 MB | Textual 8.x with TabbedContent, ~15 widgets |
| aiohttp server (idle) | ~3–5 MB | Event loop + connection pool + middleware |
| `mode_switcher.ModeSwitcher` | ~0.3 MB | State machine + LogBuffer (200 lines) |
| `SystemStats` polling | ~0.5 MB | Ephemeral string allocations |
| `MatrixRain` screensaver | ~0.5–2 MB | Full-screen string buffer (80×24 = ~10KB chars + markup) |
| Buffers & overhead (asyncio, socket, FS cache) | ~5–10 MB | Guestimate |
| **Total idle (dashboard only)** | **~22–38 MB** | |
| **During mode switch (short spike)** | +5–10 MB | Subprocess spawn, JSON parsing, IPC setup |

### 4.2 Budget vs. Reality

| Source | Target | Actual | Status |
|---|---|---|---|
| Product guidelines (Section 3.1) | TUI core ≤ 20 MB | ~22–38 MB | ⚠️ Over budget |
| Product guidelines | Telemetry ≤ 2 MB | ~0.5 MB | ✅ OK |
| Product guidelines | Network listener ≤ 5 MB | ~3–5 MB | ✅ OK |
| Product guidelines | Total ≤ 27 MB | ~22–38 MB | ⚠️ Over budget |
| 1 GB system headroom | Available for apps | ~950 MB after OS | ✅ Plenty of headroom* |

*\* While the absolute numbers show headroom, the risk is cumulative — each background process, kernel cache, and display buffer stack adds up. On a 1 GB system running mpv (which may allocate framebuffer memory), every MB counts.*

### 4.3 Potential Memory Leaks / Growth Vectors

1. **`MatrixRain` widget — unbounded string allocation**  
   `tick()` rebuilds the entire screen string every 350ms (`"\n".join(lines)`). For a 1920×1080 terminal (240×60 chars), this is ~15 KB per frame. Python string allocation for full-screen markup can spike to 2+ MB during rendering if the terminal is large. **Risk: proportional to terminal resolution.**

2. **`LogBuffer` — fixed capacity, but no de-duplication**  
   200 lines maximum, but the `replay_log_buffer()` method clears and re-pushes all lines. Each API request, button press, or polling cycle adds a line. Over hours of uptime with 5-second polling, this is ~720 lines/hour — capped at 200, so steady-state is safe.

3. **`run_sys_cmd()` — subprocess churn**  
   Creates a new shell subprocess per call. At 4+ calls every 5 seconds (settings polling), that's ~48+ subprocesses per minute. Each Python subprocess allocates pipes, buffers, and a process table entry. The kernel handles recycling, but there is a transient allocation spike per call (~200–500 KB transient per subprocess).

4. **aiohttp `AppRunner` / `TCPSite`**  
   No visible cleanup of idle connections. In normal LAN use with 1–2 clients, this is negligible. Under sustained hammering (many concurrent requests), connection pool memory could grow.

5. **Textual CSS / widget tree**  
   No dynamic widget creation/destruction after mount (except `IdleScreen` push/pop). This is good — stable widget tree means stable memory.

---

## 5. Bottleneck Analysis (1 GB RAM Constraint)

### 5.1 Critical Bottlenecks

#### 🔴 CRITICAL: `MatrixRain` Screensaver Rendering

- **File:** `tui.py`, class `MatrixRain`, method `tick()`
- **Frequency:** Every 350ms (set_interval(0.35))
- **Behavior:** Rebuilds a complete screen-height string from scratch, iterating over every column × row with random character selection, then calls `self.update()` which triggers Textual re-render.
- **Memory impact:** Full-screen string allocation grows with terminal dimensions. At 240×60 chars → ~15 KB per frame, Python creates and discards the entire string each tick.
- **CPU impact:** O(width × height) string building, string concatenation, Textual markup injection (`[bold white]`, `[green]`, etc.). On a 1 GB RPi (typically ARM Cortex-A53/A72), this can cause **noticeable UI stutter** when combined with the 2s telemetry timer and 5s settings timer.
- **Risk:** Moderate (CPU contention rather than RAM exhaustion, but the string allocation contributes to GC pressure and heap fragmentation)

#### 🔴 CRITICAL: No Explicit RAM Monitoring / Throttling

- The `SystemStats` widget **reads** RAM usage from `/proc/meminfo` but **never acts on it**. There is no:
  - Warning when RAM < 100 MB free
  - Automatic screensaver disable when memory is low
  - Throttling of `MatrixRain` frame rate based on free memory
  - GC forcing before heavy operations
- **Risk:** The dashboard could happily render `MatrixRain` while the system is OOM, accelerating the kernel OOM killer targeting critical processes.

#### 🟡 HIGH: Subprocess Storm in Settings Polling

- `update_settings_data()` spawns **4+ shell subprocesses every 5 seconds** with no concurrency limit or staggered scheduling:
  1. `ip -br addr | grep -v 'lo' | awk '{print $1 ": " $3}'`
  2. `tailscale ip -4`
  3. `pactl get-default-sink` + `pactl list short sinks`
  4. `bluetoothctl devices Paired` (fallback `bluetoothctl devices`)
  5. `grep -m1 '^ssid=' /etc/hostapd/rpi-service.conf | cut -d'=' -f2`
  6. `cat /var/lib/misc/dnsmasq.leases 2>/dev/null | wc -l`
  7. `systemctl is-active hostapd`
  8. `systemctl is-active raspotify`
- Each subprocess:
  - Forks a shell (`/bin/sh -c ...`)
  - Allocates pipe buffers (default 64 KB per pipe × 2 = 128 KB per subprocess)
  - Creates two `asyncio.subprocess.PIPE` buffers (read until process end)
  - Stays alive for ~50–300ms each
- **Peak transient allocation:** ~8 × 200 KB ≈ 1.6 MB every 5 seconds, plus the child process memory (which is charged to the child's RSS, but the parent OOM score includes fork cost).
- **Risk:** On a busy system (e.g., mpv playing a video), this periodic subprocess storm competes for memory during critical playback.

#### 🟡 HIGH: aiohttp API Server Always-On

- The API server runs on `0.0.0.0:8090` (by default) regardless of whether anyone connects to it. The `api_task` is created in `on_mount()` and never stopped.
- **Memory:** ~3–5 MB baseline, but if embedded in the same process as the TUI, it adds to the Python heap that can't be swapped.
- **No connection limits:** aiohttp default `max_connections` is non-trivial; under many idle connections (unlikely on LAN, but possible), each consumes memory.
- **Risk:** Low under normal use, but a memory exhaustion attack vector.

#### 🟡 HIGH: Multiprocess Concurrent Telemetry

- The `SystemStats` polling (2s), `update_settings_data` (5s), `MatrixRain` tick (0.35s), and API server (event-driven) all run in the **same asyncio event loop**. While asyncio is cooperative, the shell subprocess calls (`run_sys_cmd`) are genuinely concurrent (create_subprocess_shell is async), so multiple subprocesses can be alive simultaneously during polling.
- **Peak concurrent subprocesses:** During `update_settings_data()`, all 4+ `await self.run_sys_cmd()` calls are sequential within the method, but the method runs concurrently with `SystemStats` tick (2s) and `MatrixRain` tick (0.35s). So worst case: 1 (SystemStats) + 0–4 (settings, sequentially resolved) + 0 (MatrixRain is pure Python) = up to 5 simultaneous subprocesses.
- **Risk:** Low on a 1 GB system with 5 small subprocesses, but contributes to process table pressure.

### 5.2 System-Level Constraints

| Constraint | Detail | Impact on Architecture |
|---|---|---|
| **1 GB RAM shared with GPU** | On RPi, GPU memory (typically 64–256 MB via `gpu_mem` in config.txt) is carved from the same 1 GB. Actual available RAM: ~750–960 MB. | Reduces the effective headroom. mpv with hardware acceleration may use GPU memory. |
| **No swap configured** | Raspberry Pi OS Lite has swap by default (100 MB on SD card), but SD card swap is extremely slow (0.5–5 MB/s). Swapping a Python process makes the UI unusable. | Any RAM overcommit leads to severe UI lag or OOM. |
| **Single-threaded Python GIL** | Textual + asyncio run in one thread. `run_in_executor` is used only for `subprocess.Popen().wait()` (blocking wait). | MatrixRain's CPU-intensive string building blocks the event loop, delaying API responses and telemetry updates. |
| **No desktop environment** | No X11/Wayland compositor overhead by design. | This is the project's biggest memory win — saves 100–300 MB vs Kodi or Electron alternatives. |

### 5.3 Mode-Specific Bottlenecks

#### SteamLink Mode
- **Command:** `steamlink` (no arguments)
- **Risk:** SteamLink is a full-screen application that may allocate significant GPU memory. If launched when system RAM is low, it may fail silently.
- **Fallback:** Falls to `nano` if `steamlink` binary not found — useful for testing but confusing in production.

#### GeForce Now (via Moonlight)
- **Command:** `moonlight stream 192.168.0.67 "GeForce Now"`
- **Risk:** Moonlight decoding on RPi 3B (no hardware HEVC decoder) could use significant CPU/RAM. On a 1GB system with software decoding, 1080p streaming may be impossible.
- **Note:** RPi 3B only has hardware H.264 decoding. Moonlight may fall back to software, consuming 100% CPU and allocating large packet buffers.

#### MPV (media playback)
- **Command:** `mpv --fs --input-ipc-server=/tmp/mpv-socket <url>`
- **Risk:** yt-dlp-streamed content may buffer to RAM (especially `--cache`). mpv default cache size is 25 MB for network streams, but can grow with `--demuxer-max-bytes`.
- **IPC socket:** `/tmp/mpv-socket` is created as a unix socket — no memory overhead but a file descriptor.

#### Spotify (WPE WebKit)
- **Command:** `wpe` (WebKit Process Embedding)
- **Risk:** WPE WebKit is a full browser engine. Even lightweight, WPE can use 50–100 MB+ RAM for rendering web pages. On a 1 GB system, this is the heaviest mode.
- **Fallback:** Falls to `top` if `wpe` not found.

#### Amazon Music (Chromium Kiosk)
- **Command:** `chromium --kiosk --autoplay-policy=no-user-gesture-required https://music.amazon.com`
- **🚩 CRITICAL RISK:** Chromium on a 1 GB RPi is extremely heavy. Even in kiosk mode, Chromium uses 150–300 MB RAM minimum. This **will OOM** the system if launched with insufficient free memory.
- **Recommendation:** This mode should have a pre-flight memory check before launch.

---

## 6. Inefficiencies & Anti-Patterns

### 6.1 Code-Level Issues

1. **`mode_switcher._handle_sigterm`** — calling `asyncio.create_task()` in a signal handler is unsafe. Signal handlers run in the main thread but outside the event loop. The task is created but may never execute if the loop is blocked. Should use `loop.call_soon_threadsafe()` instead.

2. **`LogBuffer.clear()` is never called** — the buffer only grows to 200 then stops, but `clear()` exists and is not used anywhere. No reset mechanism.

3. **`run_sys_cmd()` — no timeout** — if a shell command hangs (e.g., `bluetoothctl` with a stuck adapter), the coroutine hangs indefinitely, blocking `update_settings_data()` and all subsequent polls.

4. **`api_middleware()` exception handling** — writes to `/tmp/api_error.log` without rotation. Over time, this file grows unboundedly (though low traffic makes this theoretical).

5. **`MatrixRain` string concatenation** — builds lines with `"".join()` and `" ".join()` per cell, plus `"\n".join()` for the full screen. Multiple intermediate string allocations per tick. A `StringIO` buffer would be more memory-efficient.

6. **`INACTIVITY_TIMEOUT = 999999.0`** — hardcoded to essentially "off." This means the MatrixRain screensaver (a memory consumer) is effectively **never activated** during normal use. The screensaver code is shipped but dead code in practice.

7. **Hardcoded paths** — `dashboard.service` hardcodes `WorkingDirectory=/home/%i/rpi-dashboard` and `ExecStart=.../rpi-dashboard/.venv/bin/python`. If repo is cloned elsewhere (e.g., `/media/Backup/RPi`), the service will fail.

### 6.2 Design-Level Issues

1. **No caching in settings polling** — `update_settings_data()` re-queries all system state every 5 seconds. Audio sinks rarely change; Bluetooth devices rarely change during a session. The subprocess storm could be reduced by event-driven updates (e.g., D-Bus signals for audio/Bluetooth changes) or simple TTL caching.

2. **`SystemStats.get_ram_usage()` returns tuple, but `update_stats` converts differently** — the method returns `(used_GB, total_GB)`, and the display conditionally shows MB vs GB units. The calculation truncates to 2 decimals. Minor precision issue.

3. **`ModeSwitcher.replay_log_buffer()` called after every resume** — `launch()` method calls `app.replay_log_buffer()` unconditionally in the finally block. If the Log widget hasn't been initialized yet (e.g., during early startup), it silently fails. This is safe but wasteful during early mounts.

4. **Headless mode duplicates all API routes** — `tui.py` has a complete copy of all 13 route handlers in the `__main__` headless block. This is a maintenance burden — any new route must be added in two places.

5. **Exception-driven fallback for missing binaries** — `on_button_pressed()` checks `shutil.which()` for each binary and falls back to `nano`, `top`, etc. These fallbacks are developer aids, not production-safe. In production, missing binaries should log a clear error.

---

## 7. RAM-Specific Risk Scenarios

| Scenario | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Chromium kiosk launched with <200 MB free | Low (manual action) | **OOM kill**, dashboard crash, TV goes black | Pre-flight memory check in `launch_mode()` |
| Multi-hour playback with streaming cache | Medium | mpv cache grows to 100+ MB, leaving little for dashboard resume | Limit mpv cache (`--cache=32768`), monitor during playback |
| MatrixRain + settings polling + API flood | Low (local network only) | UI stutter, delayed resume after mode exit | Throttle MatrixRain tick rate, coalesce shell commands |
| Memory leak in Textual or Python runtime | Unknown | Gradual degradation over days of uptime | Add periodic `gc.collect()` + log memory trend |
| SD card swap thrashing | Medium (if OOM-edge) | **Extreme UI lag**, unusable system | Monitor `vmstat` swappiness, alert before swap-in |

---

## 8. Recommendations

### 8.1 Critical (RAM Constraint)

1. **Add pre-flight memory check in `launch_mode()`** — Before spawning any external process, read `/proc/meminfo` and calculate `MemAvailable`. Reject the launch with a log message if free RAM is below a safe threshold:
   - SteamLink / Moonlight: ≥ 100 MB free
   - MPV: ≥ 150 MB free
   - WPE WebKit: ≥ 200 MB free
   - Chromium kiosk: **≥ 350 MB free**

2. **Throttle or disable `MatrixRain` based on free memory** — If `MemAvailable` drops below 200 MB, halve the tick rate. Below 100 MB, disable the screensaver entirely and display a warning.

3. **Implement `gc.collect()` in the suspend/resume cycle** — Before and after mode switching, call `gc.collect()` to reclaim any cyclic garbage. Mode switching is the natural point where memory can be freed.

4. **Reduce settings polling frequency** — 5 seconds is aggressive for mostly static data. Consider:
   - Audio sinks: poll every 30s
   - Bluetooth devices: poll every 60s
   - Network info: poll every 30s
   - Hotspot status: poll every 30s
   - Only rush the initial poll on mount.

5. **Replace shell subprocess calls with Python library calls where possible** — Specifically:
   - Replace `pactl` with `pulsectl` or `pulseaudio-asyncio` Python library (avoids ~4 subprocesses per settings poll)
   - Replace `bluetoothctl` with `pydbus` / D-Bus bindings (avoids ~2 subprocesses)
   - Replace `systemctl is-active` with Python `systemd.dbus` bindings or reading `/run/systemd/units/`

### 8.2 High Priority

6. **Set mpv cache limits explicitly** — Pass `--cache=32768 --demuxer-max-bytes=64M` to limit mpv memory usage during streaming.

7. **Add subprocess timeout to `run_sys_cmd()`** — Default 10s timeout prevents hanging on stuck Bluetooth/Wi-Fi commands.

8. **Use `asyncio.create_subprocess_exec()` instead of `create_subprocess_shell()`** — Avoid the intermediate shell fork, reducing memory and process table pressure.

9. **Cache known-unchanging values** — Add a simple TTL dict cache in `RPiDashboard` (e.g., `_cached_network_info` with 30s expiry) to avoid redundant shell calls.

### 8.3 Medium Priority

10. **Deduplicate API routes** — Extract route definitions into a shared module (e.g., `api_routes.py`) used by both full TUI mode and headless mode.

11. **Fix signal handler safety** — Replace `asyncio.create_task()` in `_handle_sigterm` and `_handle_sigint` with `loop.call_soon_threadsafe()`.

12. **Add log rotation for `/tmp/api_error.log`** — Truncate or rotate to prevent unbounded disk growth (theoretical risk, but good practice).

13. **Document the `INSTALL_DIR` vs `dashboard.service` alignment** — Add a note to `provisioning/README.md` warning that `INSTALL_DIR` override requires manually editing the service file.

---

## 9. Architectural Strengths

The architecture has several well-considered design choices that minimize RAM pressure:

1. **Process isolation** — External apps never run in-process. The TUI heap is not polluted by mpv/Chromium allocations.
2. **Textual suspend/resume** — Full TUI suspension during mode execution releases the Textual rendering engine and its Python heap to be swapped/paged. When mpv runs, the dashboard's ~30 MB heap is cold memory but not actively allocated.
3. **No desktop environment** — The biggest RAM savings (200–400 MB vs X11/LXDE/Kodi).
4. **Async-first design** — Single event loop with cooperative multitasking avoids thread overhead.
5. **LogBuffer ring buffer** — Fixed-size, no unbounded growth.
6. **State machine guards** — Prevents concurrent mode launches that would multiply memory usage.
7. **Idempotent provisioning** — Safe to re-run, making recovery from misconfiguration easy.

---

## 10. Conclusion

The RPi Dumb TV Dashboard is a well-architected, purpose-built application that respects its 1 GB RAM constraint through careful design choices (no desktop environment, process isolation, async architecture, Textual over heavier frameworks). The core TUI footprint of ~22–38 MB is close to the 27 MB budget and is not a problem in absolute terms.

**The primary risks are:**

1. **Chromium kiosk mode** — The heaviest mode by far (150–300 MB) and the most likely to cause OOM. Should have a pre-flight memory check.
2. **Subprocess storm in settings polling** — 4+ shell subprocesses every 5 seconds creates unnecessary transient memory pressure and process table churn. Mitigable by Python library replacements or reduced polling frequency.
3. **`MatrixRain` CPU/memory cost** — Full-screen string rebuild every 350ms adds CPU and memory allocation pressure. Currently dead code (timeout disabled) but should be throttled on low-RAM systems if ever enabled.
4. **No proactive memory management** — The dashboard reads RAM but never acts on it. Adding pre-flight checks and adaptive throttling would make the system resilient.

With the recommendations above (especially #1, #3, #4, #5, #7), the dashboard can operate reliably within the 1 GB constraint even under multi-day uptime and concurrent media playback.

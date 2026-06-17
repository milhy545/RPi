# Implementation Plan: DLNA/UPnP Rendering

## Phase 1: Research & Prototype
- [x] Task: Test compile `gmrender-resurrect` on RPi
  - Build script created: `provisioning/06-install-gmrender.sh`
  - Installs build deps, clones repo, compiles and installs
- [x] Task: Systemd service created
  - Service file: `provisioning/gmrender-resurrect.service`
  - Memory limit: 50M, CPU quota: 50%
  - Auto-restart on failure

## Phase 2: Integration
- [x] Task: Backend API endpoints
  - `GET /dlna/renderer/status` — running, pid, uptime, installed, pipewire, ready
  - `GET /dlna/renderer/start` — start renderer (systemd or direct)
  - `GET /dlna/renderer/stop` — stop renderer (systemd or signal)
- [x] Task: Backend functions
  - `dlna_renderer_status()` — full status check
  - `dlna_renderer_start()` — start with systemd/direct fallback
  - `dlna_renderer_stop()` — stop with signal fallback
  - `_gmrender_running()` — process check
  - `_gmrender_pid()` — PID retrieval
  - `_gmrender_uptime()` — process uptime
- [x] Task: WebUI integration
  - DLNA Renderer section in Audio tab
  - Status display: RUNNING/STOPPED/NOT INSTALLED, READY/NOT READY
  - Start/Stop buttons with proper disabled states
  - PID, uptime, PipeWire status display
  - Install hint when gmrender-resurrect not found
  - Auto-refresh on taRefresh()

## Phase 3: Validation
- [x] `py_compile` passes for webserver_8099.py
- [x] Selftest (selftest_testaudio) passes with ok: True
- [x] All new functions tested: dlna_renderer_status, _gmrender_running, _gmrender_pid
- [x] HTML page contains all DLNA renderer elements
- [x] No regression to existing playback, audio, devices, and terminal flows

## Next Steps (manual on RPi)
1. Run `provisioning/06-install-gmrender.sh` to build and install gmrender-resurrect
2. Copy `provisioning/gmrender-resurrect.service` to `/etc/systemd/system/`
3. Run `sudo systemctl daemon-reload && sudo systemctl enable gmrender-resurrect`
4. Test from mobile with BubbleUPNP or similar DLNA controller
5. Verify RPi appears as "RPi Renderer" in DLNA scan

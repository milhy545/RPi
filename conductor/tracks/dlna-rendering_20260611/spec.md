# Specification: DLNA/UPnP Rendering

## Goal
Enable the RPi to act as a DLNA/UPnP MediaRenderer so it can receive and play audio/video streams from DLNA controllers (mobile apps, other devices).

## Current State
- **DLNA Scan works:** `gssdp-discover` finds 2 MediaRenderers (LG TV, WiiMu)
- **DLNA Rendering missing:** No UPnP renderer service running on RPi
- **Available sinks:** HDMI, Bluetooth, USB — but no DLNA sink exposed

## Requirements
1. **UPnP MediaRenderer Service:** RPi announces itself as a DLNA renderer
2. **Audio Playback:** Receive streams via UPnP AVTransport → play via mpv/PipeWire
3. **Video Playback (optional):** Receive video streams → play via mpv on DRM/KMS
4. **Integration:** Control via existing WebUI/API (port 8099)
5. **Low RAM:** Renderer daemon < 50 MB

## Options
| Option | Pros | Cons |
|---|---|---|
| **gmrender-resurrect** | Lightweight C/GStreamer, ~20 MB | Not in Debian 12/backports, needs compile |
| **rygel** | Full UPnP/DLNA server+renderer | Heavy (~100 MB), not in Debian 12 |
| **pulseaudio-dlna** | Simple, uses PulseAudio/PipeWire | Not in Debian 12/backports |
| **Kodi as UPnP renderer** | Already mature, supports audio/video | Heavy if full Kodi, but can run headless |
| **Custom Python + GStreamer** | Full control, minimal | Development effort |

## Preferred Approach
**Option A (Quick):** Compile `gmrender-resurrect` from source (lightweight, ~20 MB)
**Option B (Integration):** Run Kodi in headless mode as UPnP renderer (reuses existing `kodi_rpc` in webserver)

## Acceptance Criteria
- [ ] RPi appears as "RPi Renderer" in DLNA controllers (BubbleUPnP, etc.)
- [ ] Can play audio stream from mobile to RPi → BT Soundbar
- [ ] WebUI shows DLNA renderer status
- [ ] RAM overhead < 50 MB
- [ ] Survives reboot (systemd service)
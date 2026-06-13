# Implementation Plan: DLNA/UPnP Rendering

## Phase 1: Research & Prototype
- [ ] Task: Test compile `gmrender-resurrect` on RPi
  - Install build deps: `gstreamer1.0-libav gstreamer1.0-plugins-base gstreamer1.0-plugins-good`
  - Clone and build: `git clone https://github.com/hzeller/gmrender-resurrect`
  - Test: `./gmrender-resurrect -f "RPi Renderer" -g 1`
- [ ] Task: Alternative: Test Kodi headless as UPnP renderer
  - Install: `apt install kodi`
  - Configure: `kodi --headless --upnp-renderer`
  - Test via BubbleUPnP

## Phase 2: Integration
- [ ] Task: Create systemd service for chosen renderer
- [ ] Task: Add renderer status to WebUI (`/dlna/renderer/status`)
- [ ] Task: Add renderer control to WebUI (enable/disable)
- [ ] Task: Integrate with existing audio routing (PipeWire → BT/HDMI)

## Phase 3: Validation
- [ ] Task: Test from mobile (BubbleUPnP, AVRemote)
- [ ] Test audio stream: play MP3 from phone → RPi → BT Soundbar
- [ ] Test video stream (if supported): play MP4 from phone → RPi → HDMI
- [ ] Verify RAM usage < 50 MB
- [ ] Conductor - User Manual Verification 'dlna-rendering'
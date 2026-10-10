# Project Overview

## What this project is
`rpi-dashboard` is a low-RAM Raspberry Pi TV dashboard that acts as a launcher, media controller, device manager, and WebUI control plane.

## Main runtime pieces
- `tui.py` — the main Textual dashboard
- `webserver_8099.py` — the WebUI and HTTP/WebSocket control server
- `mode_switcher.py` — launches and supervises external apps without breaking the dashboard state
- `keys2mpv.py` — multimedia-key daemon that talks directly to mpv IPC
- `main.py` — minimal entry point used for smoke tests and packaging checks

## System layout
- **Player tab**: YouTube/mpv playback and age/cookie diagnostics
- **Audio tab**: outputs, inputs, mixer, routing, and DLNA compensation
- **Devices tab**: Bluetooth pairing and Wi‑Fi management
- **Kodi tab**: legacy JSON-RPC launcher for a local Kodi instance
- **Terminal tab**: tmux-backed terminal access over WebSocket

## Real usage examples
- Open the WebUI and paste a YouTube URL into `Player` to start playback.
- Use `Audio` to move the default sink between BT, HDMI, and DLNA.
- Use `Devices` to pair a speaker or Xbox controller, then return to `Audio` for routing.
- Use the `Terminal` tab for shell work without leaving the TV UI.

## Design rules captured in this project
- No heavy desktop environment on the Pi
- mpv stays highest priority
- WebUI controls must be safe and low-friction
- Documentation should describe actual behavior, not aspirational behavior

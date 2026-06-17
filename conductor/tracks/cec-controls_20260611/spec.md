# Specification: CEC Controls

## Goal
Full CEC control via webUI and CEC bridge daemon for TV remote → mpv control.

## Features
1. **Power:** On (IMAGE_VIEW_ON) / Off (STANDBY)
2. **Navigation:** Up/Down/Left/Right/Select/Back/Menu/CH+/CH-
3. **Volume:** Up/Down/Mute
4. **Input Switching:** Active Source (HDMI 1/2/3)
5. **Scan:** CEC bus device discovery
6. **Bridge Daemon:** cec-client listens for TV remote events → maps to mpv IPC

## Implementation Details
- **cec-ctl** for command sending (reliable, low-level)
- **cec-client** for bridge daemon (listens for TV remote events)
- **Bridge maps:** Play/Pause/Stop/Seek/Vol/Mute → mpv IPC
- **Power On fix:** `--image-view-on` (not `--text-view-on`)
- **Auto-restart:** Bridge daemon auto-restarts if cec-client crashes

## API Endpoints
- `POST /cec/send?c=<command>` — send raw CEC command
- `POST /cec/key?k=<key>` — send user control key
- `POST /cec/in?n=<1-3>` — switch HDMI input
- `POST /cec/scan` — scan CEC bus
- `POST /cec/br/start` — start bridge daemon
- `POST /cec/br/stop` — stop bridge daemon
- `GET /cec/br/st` — bridge status

## Acceptance Criteria
- [ ] Power On/Off works (TV turns on/off)
- [ ] Navigation keys send correct CEC codes
- [ ] Volume Up/Down/Mute works
- [ ] Input switching via Active Source works
- [ ] Bridge daemon maps TV remote → mpv IPC correctly
- [ ] Bridge auto-restarts on crash
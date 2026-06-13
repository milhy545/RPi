# Specification: Terminal Tab in WebUI

## Goal
Add a Terminal tab to the webUI (port 8099) that provides a full tmux shell via WebSocket (port 8098).

## Architecture
- **WebSocket Server:** Port 8098 (separate from HTTP 8099)
- **Backend:** tmux session `RPi:1` (dedicated window with shell)
- **Frontend:** xterm.js via CDN
- **Protocol:** JSON messages `{action: "attach", session: "RPi:1"}` / `{input: "..."}`

## Features
1. **Connect/Disconnect:** Buttons to attach/detach from tmux
2. **Full Terminal:** xterm.js with 256-color support, cursor blink
3. **Diff Polling:** Server captures tmux pane (`capture-pane -S -{height}`) every 500ms, sends only changes
4. **Resize Handling:** Window resize → `FitAddon.fit()`
5. **Session:** tmux session `RPi:1` (dedicated window 1 with shell)

## WebSocket Protocol
```
Client → Server: {"action": "attach", "session": "RPi:1"}
Server → Client: {"output": "<full terminal content>", "full": true} (initial)
Server → Client: {"output": "<diff>", "full": true} (periodic updates)
Client → Server: {"input": "ls\\n"} (keystrokes)
```

## tmux Setup
- Main session: `RPi` (window 0: pi agent TUI)
- Terminal window: `RPi:1` (dedicated shell)
- Persistence: tmux-resurrect + continuum

## Acceptance Criteria
- [ ] Terminal tab appears in webUI
- [ ] Connect button establishes WebSocket
- [ ] Terminal shows prompt, accepts commands
- [ ] Output updates in real-time (500ms polling)
- [ ] Resize works
- [ ] Disconnect/Reconnect works
- [ ] Survives webserver restart (tmux persists)
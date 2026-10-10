# Implementation Plan: Terminal Tab in WebUI

## Phase 1: WebSocket Server
- [x] Task: Add `websockets` dependency to uv
- [x] Task: Implement `term_handler` async function
  - Attach to tmux session `RPi:1`
  - Poll `tmux capture-pane -S -{height}` every 500ms
  - Send diffs via WebSocket
  - Handle `input` messages → `tmux send-keys`
- [x] Task: Start WebSocket server on port 8098 in background thread

## Phase 2: Frontend
- [x] Task: Add Terminal tab to webUI tabs
- [x] Task: Include xterm.js + fit addon via CDN
- [x] Task: Implement `termInit()`, `termConnect()`, `termDisconnect()`
- [x] Task: Handle WebSocket messages → `term.write()`
- [x] Task: Handle resize → `termFit.fit()`

## Phase 3: tmux Setup
- [x] Task: Create tmux window 1 in session `RPi` with shell
- [x] Task: Configure tmux-resurrect + continuum for persistence

## Phase 4: Integration & Validation
- [x] Task: Add Terminal tab to webUI HTML
- [x] Task: Test Connect/Disconnect
- [x] Task: Test command execution (ls, echo, etc.)
- [x] Test resize handling
- [x] Test disconnect/reconnect
- [x] Conductor - User Manual Verification 'terminal-tab-webui'
# AGENTS.md - RPi Dashboard

## 🚀 Remote Execution (Critical)
- **Primary Host:** `ssh RPi`
- **Persistence:** Use tmux session `remote_kilo`.
- **Interaction:** `ssh RPi "tmux send-keys -t remote_kilo 'command' C-m"`
- **Output Check:** `ssh RPi "tmux capture-pane -p -t remote_kilo"`

## 🛠️ Key Commands
- **Dependencies:** `uv sync`
- **TUI Dashboard:** `uv run python tui.py`
- **WebUI/API:** `uv run python webserver_8099.py`
- **Verification:** `tools/verify-done.sh` (MANDATORY before claiming task is done)
- **Testing:** `pytest`

## 🏗️ Architecture Map
- `tui.py`: Textual-based interactive dashboard.
- `webserver_8099.py`: Web interface & API (including WebSocket terminal).
- `mode_switcher.py`: Foreground application state supervisor.
- `keys2mpv.py`: Multimedia keyboard → mpv command daemon.
- `conductor/`: Product specifications, workflow guidelines, and development tracks.

## ⚠️ Operational Gotchas
- **RAM Constraint:** Core TUI must remain ≤ 20 MB.
- **Deploy Pipeline:** Development on Milhy-PC → Validation in QEMU (ARM) → Deploy to real RPi.
- **Verification Rule:** If `tools/verify-done.sh` exits with code 1, the task is strictly NOT complete.

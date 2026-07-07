"""Terminal service module for RPi-TV Dashboard.

Handles WebSocket terminal and tmux integration.
"""

import subprocess
from typing import Any, Dict


def _run(cmd, t=5):
    """Run a command with timeout."""
    return subprocess.run(cmd, capture_output=True, text=True, timeout=t)


def terminal_connect() -> Dict[str, Any]:
    """Connect to terminal session."""
    try:
        # Check if tmux session exists
        r = _run(["tmux", "ls"], t=3)
        if r.returncode == 0:
            # Session exists
            return {"ok": True, "session": "rpi-dashboard"}
        else:
            # Create new session
            r2 = _run(["tmux", "new-session", "-d", "-s", "rpi-dashboard"], t=3)
            return {"ok": r2.returncode == 0, "session": "rpi-dashboard"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def terminal_disconnect() -> Dict[str, Any]:
    """Disconnect from terminal session."""
    try:
        r = _run(["tmux", "kill-session", "-t", "rpi-dashboard"], t=3)
        return {"ok": r.returncode == 0}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def terminal_send_command(command: str) -> Dict[str, Any]:
    """Send command to terminal session."""
    try:
        r = _run(["tmux", "send-keys", "-t", "rpi-dashboard", command, "Enter"], t=3)
        return {"ok": r.returncode == 0}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def terminal_capture_output() -> str:
    """Capture terminal output."""
    try:
        r = _run(["tmux", "capture-pane", "-t", "rpi-dashboard", "-p"], t=3)
        return r.stdout
    except Exception:
        return ""


def terminal_list_sessions() -> list:
    """List all tmux sessions."""
    try:
        r = _run(["tmux", "ls"], t=3)
        if r.returncode == 0:
            sessions = []
            for line in r.stdout.strip().split("\n"):
                if ":" in line:
                    name = line.split(":")[0]
                    sessions.append(name)
            return sessions
        return []
    except Exception:
        return []


def terminal_create_session(name: str = "rpi-dashboard") -> Dict[str, Any]:
    """Create a new tmux session."""
    try:
        r = _run(["tmux", "new-session", "-d", "-s", name], t=3)
        return {"ok": r.returncode == 0, "session": name}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def terminal_kill_session(name: str) -> Dict[str, Any]:
    """Kill a tmux session."""
    try:
        r = _run(["tmux", "kill-session", "-t", name], t=3)
        return {"ok": r.returncode == 0}
    except Exception as e:
        return {"ok": False, "error": str(e)}

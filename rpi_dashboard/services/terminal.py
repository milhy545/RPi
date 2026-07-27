"""Terminal service module for RPi-TV Dashboard.

Handles WebSocket terminal and tmux integration.
"""

import asyncio
import json
import subprocess
from typing import Any, Callable, Dict, Optional


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


async def terminal_ws_handler(
    websocket,
    auth_token: str,
    is_allowed_ip: Callable[[str], bool],
    session_name: str = "RPi:0",
) -> None:
    """Handle the authenticated terminal WebSocket bridge."""
    client_ip = websocket.remote_address[0] if websocket.remote_address else None
    if not client_ip or not is_allowed_ip(client_ip):
        try:
            await websocket.close(1008, "Forbidden – IP not allowed")
        except Exception:
            pass
        return

    authenticated = False
    try:
        query = websocket.request.path if hasattr(websocket, "request") and websocket.request else ""
        if f"token={auth_token}" in query:
            authenticated = True
    except Exception:
        pass

    if not authenticated:
        try:
            first_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(first_msg)
            if data.get("action") == "auth" and data.get("token") == auth_token:
                authenticated = True
            else:
                await websocket.close(1008, "Authentication required")
                return
        except (asyncio.TimeoutError, json.JSONDecodeError, Exception):
            try:
                await websocket.close(1008, "Authentication required")
            except Exception:
                pass
            return

    rows = 24
    cols = 80
    poll_task: Optional[asyncio.Task] = None

    async def resize_tmux() -> None:
        try:
            proc = await asyncio.create_subprocess_exec(
                "tmux",
                "resize-pane",
                "-t",
                session_name,
                "-x",
                str(cols),
                "-y",
                str(rows),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=1.0)
        except Exception:
            pass

    async def poll_output() -> None:
        while True:
            await asyncio.sleep(0.35)
            try:
                content = subprocess.run(
                    ["tmux", "capture-pane", "-t", session_name, "-p", "-S", f"-{rows}"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                ).stdout
                cursor_raw = subprocess.run(
                    ["tmux", "display-message", "-t", session_name, "-p", "#{cursor_x} #{cursor_y}"],
                    capture_output=True,
                    text=True,
                    timeout=1,
                ).stdout.strip().split()
                cursor_x = int(cursor_raw[0]) if len(cursor_raw) >= 1 and cursor_raw[0].isdigit() else 0
                cursor_y = int(cursor_raw[1]) if len(cursor_raw) >= 2 and cursor_raw[1].isdigit() else 0
                all_lines = content.splitlines()
                start = max(0, len(all_lines) - rows)
                lines = all_lines[start:]
                normalized = "\r\n".join(line[:cols] for line in lines)
                rel_y = max(0, min(rows - 1, cursor_y)) if all_lines else 0
                rel_x = max(0, min(cols - 1, cursor_x))
                await websocket.send(json.dumps({"output": normalized, "full": True, "cursor": {"x": rel_x, "y": rel_y}}))
            except Exception:
                break

    try:
        async for message in websocket:
            try:
                data = json.loads(message)
            except Exception:
                continue
            if data.get("action") == "attach":
                session_name = data.get("session", "RPi")
                rows = max(10, min(80, int(data.get("rows") or rows)))
                cols = max(40, min(220, int(data.get("cols") or cols)))
                await resize_tmux()
                if poll_task:
                    poll_task.cancel()
                poll_task = asyncio.create_task(poll_output())
            elif data.get("resize"):
                r = data.get("resize") or {}
                rows = max(10, min(80, int(r.get("rows") or rows)))
                cols = max(40, min(220, int(r.get("cols") or cols)))
                await resize_tmux()
            elif data.get("input"):
                try:
                    inp = data["input"]
                    special_keys = {
                        "\r": "Enter",
                        "\n": "Enter",
                        "\x7f": "BSpace",
                        "\b": "BSpace",
                        "\t": "Tab",
                        "\x03": "C-c",
                        "\x04": "C-d",
                        "\x1b[A": "Up",
                        "\x1b[B": "Down",
                        "\x1b[C": "Right",
                        "\x1b[D": "Left",
                        "\x1b[3~": "Delete",
                        "\x1b[H": "Home",
                        "\x1b[F": "End",
                    }
                    if inp in special_keys:
                        proc = await asyncio.create_subprocess_exec(
                            "tmux",
                            "send-keys",
                            "-t",
                            session_name,
                            special_keys[inp],
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        await asyncio.wait_for(proc.communicate(), timeout=1.0)
                    else:
                        proc = await asyncio.create_subprocess_exec(
                            "tmux",
                            "send-keys",
                            "-t",
                            session_name,
                            "-l",
                            inp,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        await asyncio.wait_for(proc.communicate(), timeout=1.0)
                except Exception:
                    pass
    finally:
        if poll_task:
            poll_task.cancel()

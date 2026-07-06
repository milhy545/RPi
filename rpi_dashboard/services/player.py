"""Player service module for RPi-TV Dashboard.

Handles mpv player control, playback, and IPC communication.
"""

import json
import os
import re
import socket
import subprocess
import sys
import time
from typing import Any, Dict, Optional

# Constants
MSOCK = "/tmp/rpi-mpv.sock"
SOCKET_RECV_SIZE = 4096
MPV_CONNECT_TIMEOUT = 2

# YouTube URL pattern
YT_RE = re.compile(r"(?:youtu\.be/|youtube\.com/(?:watch\?.*?[?&]?v=|embed/|shorts/))([A-Za-z0-9_-]{11})")

# Quality presets
QUALITY = {
    "360p": "best[height<=360][ext=mp4]/best[height<=360]",
    "480p": "best[height<=480][ext=mp4]/best[height<=480]",
    "720p": "best[height<=720][ext=mp4]/best[height<=720]",
    "1080p": "best[height<=1080][ext=mp4]/best[height<=1080]",
}
DQ = "720p"


def _run(cmd, t=5):
    """Run a command with timeout."""
    return subprocess.run(cmd, capture_output=True, text=True, timeout=t)


def mpv_ipc_socket_live() -> bool:
    """Check if mpv IPC socket is alive."""
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(MPV_CONNECT_TIMEOUT)
        s.connect(MSOCK)
        s.sendall(json.dumps({"command": ["get_property", "idle-active"]}).encode() + b"\n")
        d = s.recv(SOCKET_RECV_SIZE)
        s.close()
        return bool(d)
    except Exception:
        return False


def mcmd(*a) -> Any:
    """Send command to mpv via IPC socket."""
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(MPV_CONNECT_TIMEOUT)
        s.connect(MSOCK)
        r = {"jsonrpc": "2.0", "method": "command", "params": list(a), "id": 1}
        s.sendall(json.dumps(r).encode() + b"\n")
        d = s.recv(SOCKET_RECV_SIZE)
        s.close()
        dec = json.JSONDecoder()
        probe = d.decode("utf-8", "replace").lstrip()
        obj, _ = dec.raw_decode(probe)
        return obj.get("data", obj.get("result"))
    except Exception:
        return None


def mget(p: str) -> Any:
    """Get mpv property."""
    return mcmd("get_property", p)


def mset(p: str, v: Any) -> Any:
    """Set mpv property."""
    return mcmd("set_property", p, v)


def mpv_start(url: str, quality: Optional[str] = None, resume: bool = False) -> Dict[str, Any]:
    """Start mpv playback."""
    q = quality or DQ
    yt_filter = QUALITY.get(q, QUALITY[DQ])

    # Build mpv command
    cmd = [
        "mpv",
        "--fullscreen",
        "--no-terminal",
        "--input-ipc-server=" + MSOCK,
        "--ytdl",
        "--ytdl-format=" + yt_filter,
        "--keep-open=always",
        "--framedrop=vo",
        "--hwdec=auto",
        "--vo=gpu,x11,drm",
        "--ao=pulse",
    ]

    if resume:
        cmd.append("--start=0")

    cmd.append(url)

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        return {"ok": True, "pid": proc.pid}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mpv_stop() -> Dict[str, Any]:
    """Stop mpv playback."""
    try:
        # Try graceful shutdown via IPC
        if mpv_ipc_socket_live():
            mcmd("quit")
            time.sleep(0.5)

        # Kill any remaining mpv processes
        r = _run(["pkill", "-f", "mpv"], t=3)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mpv_st() -> Dict[str, Any]:
    """Get mpv status."""
    if not mpv_ipc_socket_live():
        return {"ok": False, "on": False, "err": "mpv not running"}

    try:
        pos = mget("time-pos") or 0
        dur = mget("duration") or 0
        paused = mget("paused") or False
        title = mget("media-title") or ""
        vol = mget("volume") or 100
        idle = mget("idle-active") or False

        return {
            "ok": True,
            "on": True,
            "pos": pos,
            "dur": dur,
            "paused": paused,
            "title": title,
            "vol": vol,
            "q": DQ,
            "idle": idle,
        }
    except Exception as e:
        return {"ok": False, "on": False, "err": str(e)}


def mpv_seek(position: float) -> Dict[str, Any]:
    """Seek to position in seconds."""
    try:
        mset("time-pos", position)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mpv_volume(volume: int) -> Dict[str, Any]:
    """Set mpv volume (0-150)."""
    try:
        vol = max(0, min(150, volume))
        mset("volume", vol)
        return {"ok": True, "volume": vol}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mpv_pause() -> Dict[str, Any]:
    """Toggle pause."""
    try:
        paused = mget("paused")
        mset("paused", not paused)
        return {"ok": True, "paused": not paused}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mpv_next() -> Dict[str, Any]:
    """Play next item in playlist."""
    try:
        mcmd("playlist-next")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mpv_previous() -> Dict[str, Any]:
    """Play previous item in playlist."""
    try:
        mcmd("playlist-prev")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mpv_subtitle_add(url: str) -> Dict[str, Any]:
    """Add subtitle file."""
    try:
        mcmd("sub-add", url)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mpv_audio_delay(delay_ms: int) -> Dict[str, Any]:
    """Set audio delay in milliseconds."""
    try:
        mset("audio-delay", delay_ms / 1000.0)
        return {"ok": True, "delay_ms": delay_ms}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mpv_ended() -> bool:
    """Check if mpv has ended playback (EOF)."""
    if not mpv_ipc_socket_live():
        return False
    try:
        idle = mget("idle-active")
        eof = mget("eof-reached")
        return bool(idle or eof)
    except Exception:
        return False


def mpv_listen_for_eof(callback=None, check_interval: float = 1.0) -> bool:
    """Listen for mpv EOF event and trigger callback.
    
    Args:
        callback: Function to call when EOF is detected
        check_interval: Seconds between checks
    
    Returns:
        True if listener started, False otherwise
    """
    import threading
    
    def _eof_listener():
        while True:
            time.sleep(check_interval)
            try:
                if mpv_ipc_socket_live() and mpv_ended():
                    if callback:
                        callback()
                    break
                elif not mpv_ipc_socket_live():
                    break
            except Exception:
                break
    
    thread = threading.Thread(target=_eof_listener, daemon=True)
    thread.start()
    return True


def mpv_auto_return_on_eof() -> Dict[str, Any]:
    """Set up mpv to auto-return to dashboard on EOF."""
    def on_eof():
        # Save resume memory
        save_mpv_resume_memory()
        # Stop mpv
        mpv_stop()
        print("[INFO] mpv EOF reached, returning to dashboard", file=sys.stderr)
    
    return {"ok": mpv_listen_for_eof(callback=on_eof)}


def cleanup_stale_mpv_socket() -> None:
    """Remove stale mpv socket file."""
    try:
        if os.path.exists(MSOCK):
            os.remove(MSOCK)
    except Exception:
        pass


def save_mpv_resume_memory() -> None:
    """Save current playback position for resume."""
    try:
        if not mpv_ipc_socket_live():
            return
        pos = mget("time-pos")
        dur = mget("duration")
        title = mget("media-title")
        if pos and dur and title:
            data = {
                "position": pos,
                "duration": dur,
                "title": title,
                "timestamp": time.time()
            }
            memory_file = os.path.expanduser("~/rpi-dashboard/playback-memory.json")
            with open(memory_file, "w") as f:
                json.dump(data, f)
    except Exception:
        pass


def load_mpv_resume_memory() -> Optional[Dict[str, Any]]:
    """Load saved playback position."""
    try:
        memory_file = os.path.expanduser("~/rpi-dashboard/playback-memory.json")
        if os.path.exists(memory_file):
            with open(memory_file) as f:
                return json.load(f)
    except Exception:
        pass
    return None


def yt_id(u: str) -> Optional[str]:
    """Extract YouTube video ID from URL."""
    if not isinstance(u, str):
        return None
    m = YT_RE.search(u)
    return m.group(1) if m else None

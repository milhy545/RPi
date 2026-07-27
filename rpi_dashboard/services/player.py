"""Player service module for RPi-TV Dashboard.

Handles mpv player control, playback, and IPC communication.
"""

import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
from . import return_service
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
        title = mget("media-title") or mget("filename") or mget("path") or "Playback"
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


def mpv_seek_absolute(position: float) -> Dict[str, Any]:
    """Seek to an absolute position in the current file."""
    try:
        mcmd("seek", position, "absolute")
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


def mpv_volume_delta(delta: int) -> Dict[str, Any]:
    """Adjust mpv volume by a relative delta."""
    try:
        current = mget("volume") or 100
        vol = max(0, min(150, int(current) + int(delta)))
        mset("volume", vol)
        return {"ok": True, "volume": vol, "delta": delta}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mpv_pause() -> Dict[str, Any]:
    """Toggle pause."""
    try:
        paused = bool(mget("paused"))
        mset("paused", not paused)
        return {"ok": True, "paused": not paused}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mpv_toggle() -> Dict[str, Any]:
    """Alias for pause toggle used by the API layer."""
    return mpv_pause()


def _playback_memory_file() -> str:
    return os.path.join(os.path.expanduser("~"), "rpi-dashboard", "playback-memory.json")


def _playback_media_key(url: str) -> str:
    m = YT_RE.search(url or "")
    if m:
        return m.group(1)
    return hashlib.sha256((url or "").encode()).hexdigest()[:16]


def load_mpv_resume_memory() -> Dict[str, Any]:
    """Load all saved playback resume metadata."""
    mem_file = _playback_memory_file()
    try:
        if os.path.exists(mem_file):
            with open(mem_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
    except Exception:
        pass
    return {}


def _save_playback_memory(data: Dict[str, Any]) -> None:
    mem_file = _playback_memory_file()
    os.makedirs(os.path.dirname(mem_file), exist_ok=True)
    with open(mem_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def mpv_memory_for_url(url: str) -> Optional[Dict[str, Any]]:
    """Return saved resume metadata for a URL."""
    return load_mpv_resume_memory().get(_playback_media_key(url))


def mpv_memory_clear_for_url(url: str) -> bool:
    """Remove resume metadata for a URL."""
    try:
        data = load_mpv_resume_memory()
        key = _playback_media_key(url)
        if key in data:
            del data[key]
            _save_playback_memory(data)
            return True
    except Exception:
        pass
    return False


def save_mpv_resume_memory() -> Optional[Dict[str, Any]]:
    """Save current playback position for resume."""
    try:
        if not mpv_ipc_socket_live():
            return None
        pos = mget("time-pos")
        dur = mget("duration")
        title = mget("media-title")
        if pos is None or dur is None or not title:
            return None
        position = float(pos)
        duration = float(dur)
        source_url = mget("path") or ""
        key = _playback_media_key(source_url)
        if duration > 0 and (position >= duration * 0.95 or duration - position < 30):
            mpv_memory_clear_for_url(source_url)
            return None
        if position < 5:
            return None
        data = load_mpv_resume_memory()
        memory = {
            "position": position,
            "duration": duration,
            "title": title,
            "timestamp": time.time(),
        }
        data[key] = memory
        _save_playback_memory(data)
        return memory
    except Exception:
        return None


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
        save_mpv_resume_memory()
        from . import return_service
        return_service.return_to_dashboard(reason="eof", source="mpv_eof")
    
    return {"ok": mpv_listen_for_eof(callback=on_eof)}


def cleanup_stale_mpv_socket() -> None:
    """Remove stale mpv socket file."""
    try:
        if os.path.exists(MSOCK):
            os.remove(MSOCK)
    except Exception:
        pass


def yt_id(u: str) -> Optional[str]:
    """Extract YouTube video ID from URL."""
    if not isinstance(u, str):
        return None
    m = YT_RE.search(u)
    return m.group(1) if m else None

import os
import subprocess
from typing import Any, Dict, List, Optional


from .common import _run, SILENT_WAV

def _ensure_silent_wav() -> Optional[str]:
    """Ensure silent WAV file exists for keepalive."""
    wav_path = os.path.join(os.path.dirname(__file__), "..", "..", SILENT_WAV)
    if not os.path.exists(wav_path):
        try:
            # Generate silent WAV
            subprocess.run([
                "pw-cat", "-p", "--format=fltp", "--rate=48000", "--channels=2",
                "-t", "null", wav_path
            ], capture_output=True, timeout=5)
        except Exception:
            return None
    return wav_path

def _keepalive_start(sink_name: str) -> Dict[str, Any]:
    """Start keepalive stream to prevent sink suspension."""
    wav_path = _ensure_silent_wav()
    if not wav_path:
        return {"ok": False, "error": "Could not create silent WAV"}

    try:
        proc = subprocess.Popen([
            "pw-cat", "-p", "--format=fltp", "--rate=48000", "--channels=2",
            wav_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"ok": True, "pid": proc.pid}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def _keepalive_stop(sink_name: Optional[str] = None) -> bool:
    """Stop keepalive stream."""
    try:
        r = _run(["pactl", "list", "short", "sink-inputs"])
        for line in r.stdout.splitlines():
            if "pw-cat" in line and SILENT_WAV in line:
                parts = line.split()
                if len(parts) >= 1:
                    input_id = parts[0]
                    _run(["pactl", "kill-sink-input", input_id], t=3)
                    return True
    except Exception:
        pass
    return False

def _keepalive_orphans() -> List[str]:
    """Find orphaned keepalive processes."""
    orphans = []
    try:
        r = _run(["pactl", "list", "short", "sink-inputs"])
        for line in r.stdout.splitlines():
            if "pw-cat" in line and SILENT_WAV in line:
                parts = line.split()
                if len(parts) >= 3:
                    orphans.append(parts[2])  # client PID
    except Exception:
        pass
    return orphans

def _stop_keepalive_orphans() -> int:
    """Stop all orphaned keepalive processes."""
    stopped = 0
    for pid in _keepalive_orphans():
        try:
            _run(["kill", pid], t=2)
            stopped += 1
        except Exception:
            pass
    return stopped

def _keepalive_status() -> Dict[str, Any]:
    """Get keepalive status."""
    try:
        r = _run(["pactl", "list", "short", "sink-inputs"])
        active = []
        for line in r.stdout.splitlines():
            if "pw-cat" in line and SILENT_WAV in line:
                parts = line.split()
                if len(parts) >= 3:
                    active.append(parts[2])
        return {"active": len(active) > 0, "count": len(active), "pids": active}
    except Exception:
        return {"active": False, "count": 0, "pids": []}

__all__ = [
    "_ensure_silent_wav",
    "_keepalive_start",
    "_keepalive_stop",
    "_keepalive_orphans",
    "_stop_keepalive_orphans",
    "_keepalive_status"
]


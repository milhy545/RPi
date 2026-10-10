"""DLNA renderer helpers for RPi-TV Dashboard."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

from config import PA_DLNA_PORT

from . import audio

_PA_DLNA_PORT = PA_DLNA_PORT
_PA_DLNA_LOG = "/tmp/pa-dlna-webui.log"
_pa_dlna_proc: Optional[subprocess.Popen[Any]] = None


def _load_audio_latency() -> Dict[str, Any]:
    return audio._load_audio_latency()


def _save_audio_latency(data: Dict[str, Any]) -> None:
    audio._save_audio_latency(data)


def _pa_dlna_running() -> bool:
    proc = _pa_dlna_proc
    return bool(proc and proc.poll() is None)


def _start_pa_dlna() -> bool:
    global _pa_dlna_proc
    if _pa_dlna_running():
        return True
    try:
        with open(_PA_DLNA_LOG, "ab") as log:
            _pa_dlna_proc = subprocess.Popen(
                ["pa-dlna", "--nics", "eth0", "--loglevel", "info", "--port", _PA_DLNA_PORT],
                stdout=log,
                stderr=log,
            )
        return True
    except Exception:
        return False


def _stop_pa_dlna() -> None:
    global _pa_dlna_proc
    proc = _pa_dlna_proc
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
    else:
        needle = f"--port {_PA_DLNA_PORT}"
        try:
            for pid in os.listdir("/proc"):
                if pid.isdigit():
                    try:
                        with open(f"/proc/{pid}/cmdline", "rb") as f:
                            cmd = b" ".join(f.read().split(b"\0")).decode(errors="ignore")
                            if "pa-dlna" in cmd and needle in cmd:
                                os.kill(int(pid), 15)
                    except (IOError, OSError):
                        pass
        except OSError:
            pass
    _pa_dlna_proc = None


def _gmrender_running() -> bool:
    try:
        for pid in os.listdir("/proc"):
            if pid.isdigit():
                try:
                    with open(f"/proc/{pid}/cmdline", "rb") as f:
                        cmd = b" ".join(f.read().split(b"\0")).decode(errors="ignore")
                        if "gmediarender" in cmd:
                            return True
                except (IOError, OSError): pass
    except OSError: pass
    return False


def _gmrender_pid() -> Optional[int]:
    try:
        for pid in os.listdir("/proc"):
            if pid.isdigit():
                try:
                    with open(f"/proc/{pid}/cmdline", "rb") as f:
                        cmd = b" ".join(f.read().split(b"\0")).decode(errors="ignore")
                        if "gmediarender" in cmd:
                            return int(pid)
                except (IOError, OSError): pass
    except OSError: pass
    except Exception as exc:
        print(f"[WARN] Swallowed exception: {type(exc).__name__}: {exc}", file=sys.stderr)
    return None


def _gmrender_uptime(pid: Optional[int]) -> Optional[int]:
    if not pid:
        return None
    try:
        with open(f"/proc/{pid}/stat") as f:
            parts = f.read().split()
        start_ticks = int(parts[21])
        clk = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
        with open("/proc/uptime") as f:
            uptime = float(f.read().split()[0])
        start_sec = uptime - (start_ticks / clk)
        return int(uptime - start_sec)
    except Exception as exc:
        print(f"[WARN] Swallowed exception: {type(exc).__name__}: {exc}", file=sys.stderr)
    return None


def _selected_dlna_sink_name() -> Optional[str]:
    lat = _load_audio_latency()
    sel = lat.get("selected_dlna_renderer") or {}
    usn = (sel.get("usn") or "").replace("uuid:", "").split("::")[0]
    name = (sel.get("name") or "").replace("uuid:", "")
    needles = [x for x in (usn, name, name[:12]) if x]
    sinks = audio._pactl_lines("sinks")
    dlna = [s for s in sinks if audio._classify_sink(s["name"]) == "dlna_output"]
    for sink in dlna:
        if any(needle and needle in sink["name"] for needle in needles):
            return sink["name"]
    return dlna[0]["name"] if dlna else None


def dlna_scan() -> Dict[str, Any]:
    try:
        r = subprocess.run(
            ["gssdp-discover", "-n", "5", "-t", "urn:schemas-upnp-org:device:MediaRenderer:1"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        lines = r.stdout.strip().splitlines()
        devices: List[Dict[str, Any]] = []
        current: Dict[str, Any] = {}
        for line in lines:
            line = line.strip()
            if line.startswith("resource available"):
                if current:
                    devices.append(current)
                current = {}
            elif line.startswith("USN:"):
                current["usn"] = line[4:].strip()
            elif line.startswith("Location:"):
                current["location"] = line.split(":", 1)[1].strip()
        if current:
            devices.append(current)
        renderers = [device for device in devices if "MediaRenderer" in device.get("usn", "")]
        for renderer in renderers:
            usn = renderer.get("usn", "")
            renderer["name"] = usn.split("::")[0].replace("uuid:", "")[:24]
            location = renderer.get("location", "")
            renderer["host"] = (location.split(":")[1] if ":" in location else "").replace("//", "")
        return {"devices": renderers, "count": len(renderers)}
    except Exception as exc:
        return {"error": str(exc)}


def audio_select_dlna_renderer(name: str, location: str, usn: str = "") -> Dict[str, Any]:
    """Select a DLNA renderer for audio output."""
    if not name and not location and not usn:
        return {"ok": False, "error": "renderer metadata required"}
    lat = _load_audio_latency()
    lat["selected_dlna_renderer"] = {"name": name or location, "location": location, "usn": usn}
    _save_audio_latency(lat)
    return {"ok": True, "selected": lat["selected_dlna_renderer"]}


def dlna_renderer_status() -> Dict[str, Any]:
    """Get DLNA renderer status."""
    running = _gmrender_running()
    pid = _gmrender_pid()
    uptime = _gmrender_uptime(pid) if pid else None
    installed = bool(shutil.which("gmediarender"))
    pw_ok = False
    try:
        r = subprocess.run(["pactl", "list", "short", "sinks"], capture_output=True, text=True, timeout=3)
        pw_ok = r.returncode == 0
    except Exception as exc:
        print(f"[WARN] Swallowed exception: {type(exc).__name__}: {exc}", file=sys.stderr)
    return {
        "ok": True,
        "running": running,
        "pid": pid,
        "uptime": uptime,
        "installed": installed,
        "pipewire": pw_ok,
        "name": "RPi Renderer",
        "ready": installed and pw_ok,
    }


def dlna_renderer_start() -> Dict[str, Any]:
    """Start gmediarender service."""
    if _gmrender_running():
        return {"ok": True, "already": True, "status": dlna_renderer_status()}
    r = subprocess.run(["systemctl", "start", "gmrender-resurrect"], capture_output=True, text=True, timeout=10)
    if r.returncode == 0:
        time.sleep(2)
        return {"ok": True, "method": "systemd", "status": dlna_renderer_status()}
    return {"ok": False, "error": (r.stdout + r.stderr).strip()[:300], "status": dlna_renderer_status()}


def dlna_renderer_stop() -> Dict[str, Any]:
    """Stop gmediarender service."""
    if not _gmrender_running():
        return {"ok": True, "was_running": False, "status": dlna_renderer_status()}
    r = subprocess.run(["systemctl", "stop", "gmrender-resurrect"], capture_output=True, text=True, timeout=10)
    if r.returncode == 0:
        time.sleep(1)
        return {"ok": True, "method": "systemd", "status": dlna_renderer_status()}
    pid = _gmrender_pid()
    if pid:
        try:
            os.kill(pid, 15)
            time.sleep(1)
        except Exception as exc:
            print(f"[WARN] Swallowed exception: {type(exc).__name__}: {exc}", file=sys.stderr)
    return {"ok": not _gmrender_running(), "method": "signal", "status": dlna_renderer_status()}


def audio_connect_dlna() -> Dict[str, Any]:
    lat = _load_audio_latency()
    if not lat.get("selected_dlna_renderer"):
        return {"ok": False, "error": "select DLNA renderer first"}
    if not _start_pa_dlna():
        return {"ok": False, "error": "failed to start pa-dlna"}
    sink = None
    for _ in range(20):
        sink = _selected_dlna_sink_name()
        if sink:
            break
        time.sleep(1)
    if not sink:
        return {"ok": False, "error": "pa-dlna started but no DLNA sink appeared yet", "running": _pa_dlna_running()}
    r = subprocess.run(["pactl", "set-default-sink", sink], capture_output=True, text=True, timeout=5)
    audio._keepalive_start(sink)
    audio._apply_dlna_delay()
    delay = _load_audio_latency().get("dlna_output_offset_ms")
    return {
        "ok": r.returncode == 0,
        "sink": sink,
        "running": _pa_dlna_running(),
        "keepalive": audio._keepalive_status(),
        "delay": delay,
        "out": (r.stdout + r.stderr).strip()[:200],
    }


def audio_disconnect_dlna() -> Dict[str, Any]:
    audio._keepalive_stop()
    audio._reset_dlna_delay()
    _stop_pa_dlna()
    return {"ok": True, "running": _pa_dlna_running(), "delay_reset": True}


__all__ = [
    "audio_select_dlna_renderer",
    "audio_connect_dlna",
    "audio_disconnect_dlna",
    "dlna_scan",
    "dlna_renderer_status",
    "dlna_renderer_start",
    "dlna_renderer_stop",
]

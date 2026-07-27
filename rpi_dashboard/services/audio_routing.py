"""Audio routing and keepalive helpers for RPi-TV Dashboard.

This module groups the higher-level DLNA, keepalive, and Alexa routing
behaviors behind a dedicated service boundary while reusing the lower-level
PipeWire/PulseAudio primitives from ``rpi_dashboard.services.audio``.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from . import audio


# Re-export the shared lower-level helpers used by the routing layer.
_load_dlnain_mode = audio._load_dlnain_mode
_save_dlnain_mode = audio._save_dlnain_mode
_resolve_dlnain_target = audio._resolve_dlnain_target
_dlnain_loopback_running = audio._dlnain_loopback_running
_alexa_loopback_running = audio._alexa_loopback_running
_keepalive_start = audio._keepalive_start
_keepalive_stop = audio._keepalive_stop
_keepalive_orphans = audio._keepalive_orphans
_stop_keepalive_orphans = audio._stop_keepalive_orphans
_keepalive_status = audio._keepalive_status
_resolve_alexa_target = audio._resolve_alexa_target
_find_loopback_by_source = audio._find_loopback_by_source
_loopback_module_id = audio._loopback_module_id
_start_loopback = audio._start_loopback
_stop_loopback = audio._stop_loopback
_stop_loopback_by_source = audio._stop_loopback_by_source
_pactl_lines = audio._pactl_lines
_pa_dlna_running = audio._pa_dlna_running
_USB_ALEXA_SRC = audio.USB_ALEXA_SRC
_BT_SOUNDBAR_SINK = audio.BT_SOUNDBAR_SINK
_BT_SOUNDBAR_MAC = audio.BT_SOUNDBAR_MAC


def audio_keepalive(action: str, sink: Optional[str] = None) -> Dict[str, Any]:
    """Public keepalive actions for web/API callers."""
    if action == "start" and sink:
        ok = _keepalive_start(sink)
        return {"ok": ok, "active": _keepalive_status(), "orphans": _keepalive_orphans()}
    if action == "stop" and sink:
        _keepalive_stop(sink)
        return {"ok": True, "active": _keepalive_status(), "orphans": _keepalive_orphans()}
    if action == "stop_all":
        _keepalive_stop()
        killed = _stop_keepalive_orphans()
        return {"ok": True, "active": _keepalive_status(), "orphans": _keepalive_orphans(), "killed": killed}
    return {"ok": True, "active": _keepalive_status(), "orphans": _keepalive_orphans()}


def _retarget_alexa() -> Dict[str, Any]:
    """Retarget Alexa loopback to the current default output."""
    running, target, mid = _alexa_loopback_running()
    if not running:
        return {"ok": False, "error": "Alexa loopback not running"}
    new_target = _resolve_alexa_target()
    if not new_target:
        return {"ok": False, "error": "No suitable output found"}
    if target == new_target:
        return {"ok": True, "unchanged": True, "target": target}
    if mid:
        _stop_loopback(mid)
    import time
    time.sleep(0.3)
    new_mid = _start_loopback(_USB_ALEXA_SRC, new_target)
    if new_mid:
        return {"ok": True, "old_target": target, "new_target": new_target, "module_id": new_mid}
    return {"ok": False, "error": "Failed to start loopback to new target", "old_target": target}


def _dlnain_start() -> Dict[str, Any]:
    """Start DLNA input loopback from the discovered gmrender source."""
    running, src = _dlnain_loopback_running()
    if running:
        return {"ok": True, "already": True, "source": src}
    gmrender_src = None
    for source in _pactl_lines("sources"):
        name = source.get("name", "")
        if "gmediarender" in name.lower() or "gmrender" in name.lower():
            gmrender_src = name
            break
    if not gmrender_src:
        return {"ok": False, "error": "gmrender source not found in PipeWire"}
    target = _resolve_dlnain_target()
    if not target:
        return {"ok": False, "error": "No suitable output found"}
    mid = _start_loopback(gmrender_src, target)
    if mid:
        return {"ok": True, "source": gmrender_src, "target": target, "module_id": mid}
    return {"ok": False, "error": "Failed to start loopback"}


def _dlnain_stop() -> Dict[str, Any]:
    """Stop DLNA input loopback."""
    running, src = _dlnain_loopback_running()
    if not running:
        return {"ok": True, "was_running": False}
    if not src:
        return {"ok": False, "error": "DLNA input source not found"}
    stopped = _stop_loopback_by_source(src)
    return {"ok": stopped, "source": src}


def _dlnain_retarget(new_target: str) -> bool:
    """Retarget DLNA input loopback to a new sink."""
    running, src = _dlnain_loopback_running()
    if not running:
        return False
    if not src:
        return False
    lb = _find_loopback_by_source(src)
    if lb:
        _stop_loopback(lb)
    import time
    time.sleep(0.3)
    mid = _start_loopback(src, new_target)
    return mid is not None


def _audio_matrix_reset() -> Dict[str, Any]:
    """Reset audio matrix: disconnect all custom links and unload loopback modules."""
    disconnected = 0
    unloaded = 0
    try:
        r = audio._run(["pactl", "list", "short", "modules"], t=3)
        for line in r.stdout.splitlines():
            if "module-loopback" in line:
                mod_id = line.split()[0]
                audio._run(["pactl", "unload-module", mod_id], t=3)
                unloaded += 1
    except Exception:
        pass
    try:
        matrix = audio.get_audio_matrix()
        for link in matrix.get("links", []):
            out_id, in_id = link
            try:
                audio._run(["pw-link", "-d", str(out_id), str(in_id)], t=1)
                disconnected += 1
            except Exception:
                pass
    except Exception:
        pass
    return {"ok": True, "out": f"Reset done: {disconnected} links disconnected, {unloaded} loopbacks unloaded"}


def audio_route_alexa_bt(action: str) -> Dict[str, Any]:
    """High-level Alexa→BT route control."""
    if action == "stop":
        mid = _loopback_module_id()
        if mid:
            audio._run(["pactl", "unload-module", mid])
        return {"ok": True, "route": "alexa_to_bt", "on": False}
    if action == "start":
        if _loopback_module_id():
            return {"ok": True, "route": "alexa_to_bt", "on": True, "already": True}
        sources = _pactl_lines("sources")
        if not any(s.get("name") == _USB_ALEXA_SRC for s in sources):
            return {"ok": False, "route": "alexa_to_bt", "on": False, "error": "USB Alexa input is not available"}
        import subprocess
        import time

        subprocess.run(["bluetoothctl", "connect", _BT_SOUNDBAR_MAC], capture_output=True, text=True, timeout=10)
        time.sleep(1)
        sinks = _pactl_lines("sinks")
        if not any(s.get("name") == _BT_SOUNDBAR_SINK for s in sinks):
            return {"ok": False, "route": "alexa_to_bt", "on": False, "error": "BT Soundbar sink is not available after connect attempt"}
        subprocess.run(["pactl", "set-sink-volume", _BT_SOUNDBAR_SINK, "100%"], capture_output=True)
        r = audio._run([
            "pactl", "load-module", "module-loopback",
            f"source={_USB_ALEXA_SRC}", f"sink={_BT_SOUNDBAR_SINK}", "rate=48000", "channels=2",
            "channel_map=front-left,front-right", "source_dont_move=true", "sink_dont_move=true", "latency_msec=20", "remix=true",
        ], t=10)
        return {"ok": r.returncode == 0, "route": "alexa_to_bt", "on": r.returncode == 0, "out": (r.stdout + r.stderr).strip()[:300]}
    if action == "reset":
        return _audio_matrix_reset()
    return {"ok": False, "error": "bad action"}

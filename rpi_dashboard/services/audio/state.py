import json
import re
import sys
import time
from typing import Any, Dict, List, Optional

from .common import (
    _run, _pactl_lines, BT_SOUNDBAR_SINK, BT_SOUNDBAR_MAC, BT_SOUNDBAR_NAME,
    HDMI_SINK, USB_ALEXA_SRC, DLNA_SINK_KEYWORDS, SILENT_WAV, AUDIO_STATE_CACHE_TTL,
    _audio_state_cache, _audio_state_lock
)

__all__ = [
    "_sink_volume",
    "_source_volume",
    "_classify_sink",
    "_classify_source",
    "_sink_name_by_id",
    "_sink_input_streams",
    "_paired_bt_device",
    "_get_default_sink",
    "audio_set_default",
    "_audio_state_uncached",
    "audio_state",
    "_pa_dlna_running",
]


def _sink_volume(name: str) -> Optional[int]:
    """Get volume of a sink."""
    try:
        v = _run(["pactl", "get-sink-volume", name]).stdout.strip()
        m = re.search(r"/(\s*\d+)%", v)
        return int(m.group(1)) if m else None
    except Exception:
        return None


def _source_volume(name: str) -> Optional[int]:
    """Get volume of a source."""
    try:
        v = _run(["pactl", "get-source-volume", name]).stdout.strip()
        m = re.search(r"/(\s*\d+)%", v)
        return int(m.group(1)) if m else None
    except Exception:
        return None


def _classify_sink(name: str) -> str:
    """Classify sink type by name."""
    n = name.lower()
    if "hdmi" in n:
        return "hdmi"
    if n.startswith("bluez_") or n.startswith("bluez_output"):
        return "bt"
    if any(kw.lower() in n for kw in DLNA_SINK_KEYWORDS) and "lg" not in n:
        return "dlna_output"
    if "usb" in n and "input" not in n:
        return "usb_output"
    return "other"


def _classify_source(name: str) -> str:
    """Classify source type by name."""
    n = name.lower()
    if "monitor" in n:
        return "monitor"
    if n.startswith(USB_ALEXA_SRC.lower()):
        return "usb_input"
    if "xing_wei" in n or "2.4g" in n:
        return "remote_input"
    if any(kw.lower() in n for kw in DLNA_SINK_KEYWORDS):
        return "dlna_input"
    return "other"


def _sink_name_by_id(sink_id: str, sinks: List[Dict]) -> Optional[str]:
    """Find sink name by ID."""
    for s in sinks:
        if str(s["id"]) == str(sink_id):
            return s["name"]
    return None


def _sink_input_streams(sinks: Optional[List[Dict]] = None) -> List[Dict]:
    """Get active sink input streams."""
    try:
        r = _run(["pactl", "list", "short", "sink-inputs"])
        out = []
        for l in r.stdout.strip().split("\n"):
            p = l.split()
            if len(p) >= 3:
                sink_id = p[1]
                client_pid = p[2]
                if sink_id == "4294967295":
                    continue
                sink_label = _sink_name_by_id(sink_id, sinks) if sinks else None
                if not sink_label:
                    continue
                is_keepalive = False
                try:
                    pr = _run(["ps", "-o", "args=", "-p", client_pid], t=2)
                    if pr.returncode == 0 and "pw-cat" in pr.stdout and SILENT_WAV in pr.stdout:
                        is_keepalive = True
                except Exception as e:
                    print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
                out.append({
                    "id": p[0],
                    "sink_id": sink_id,
                    "sink": sink_label,
                    "client": client_pid,
                    "format": p[4] if len(p) > 4 else "",
                    "keepalive": is_keepalive
                })
        return out
    except Exception:
        return []


def _paired_bt_device(paired_text: str, mac: str = BT_SOUNDBAR_MAC) -> Dict[str, Any]:
    """Check if a Bluetooth device is paired."""
    for line in (paired_text or "").splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] == "Device" and parts[1].upper() == mac.upper():
            return {"paired": True, "mac": parts[1], "name": " ".join(parts[2:])}
    return {"paired": False, "mac": mac, "name": BT_SOUNDBAR_NAME}


def _get_default_sink() -> Optional[str]:
    """Get current default sink."""
    try:
        return _run(["pactl", "get-default-sink"]).stdout.strip()
    except Exception:
        return None


def audio_set_default(name: str) -> Dict[str, Any]:
    """Set default audio sink."""
    r = _run(["pactl", "set-default-sink", name], t=5)
    return {"ok": r.returncode == 0}


def _audio_state_uncached() -> Dict[str, Any]:
    """Get audio state without cache."""
    from .keepalive import _keepalive_status
    from .latency import _load_audio_latency
    from .matrix import _loopback_module_id

    sinks = _pactl_lines("sinks")
    sources = _pactl_lines("sources")
    default_sink = _run(["pactl", "get-default-sink"]).stdout.strip()
    default_source = _run(["pactl", "get-default-source"]).stdout.strip()
    paired = _run(["bluetoothctl", "devices", "Paired"]).stdout.strip()
    soundbar = _paired_bt_device(paired)
    loop_id = _loopback_module_id()
    latency = _load_audio_latency()
    sink_inputs = _sink_input_streams(sinks)
    bt = next((s for s in sinks if s["name"] == BT_SOUNDBAR_SINK), None)
    hdmi = next((s for s in sinks if s["name"] == HDMI_SINK), None)
    usb_in = next((s for s in sources if s["name"] == USB_ALEXA_SRC), None)
    usb_out = next((s for s in sinks if "usb" in s["name"].lower() and "input" not in s["name"].lower()), None)
    dlna_out = next((s for s in sinks if _classify_sink(s["name"]) == "dlna_output"), None)

    classified_sinks = []
    for s in sinks:
        t = _classify_sink(s["name"])
        if t == "other":
            continue
        vol = _sink_volume(s["name"])
        classified_sinks.append({"id": s["id"], "name": s["name"], "type": t, "present": True, "volume": vol, "state": s.get("state", "")})
    order = ["hdmi", "bt", "dlna_output", "usb_output"]
    classified_sinks.sort(key=lambda x: order.index(x["type"]) if x["type"] in order else 99)

    classified_sources = []
    for s in sources:
        t = _classify_source(s["name"])
        if t == "monitor":
            continue
        vol = _source_volume(s["name"])
        classified_sources.append({"id": s["id"], "name": s["name"], "type": t, "present": True, "volume": vol, "state": s.get("state", "")})

    return {
        "default_sink": default_sink,
        "default_source": default_source,
        "sinks": classified_sinks,
        "sources": classified_sources,
        "sink_inputs": sink_inputs,
        "devices": {
            "hdmi": {"present": bool(hdmi), "type": "hdmi", "name": HDMI_SINK, "volume": _sink_volume(HDMI_SINK) if hdmi else None, "state": hdmi.get("state") if hdmi else None},
            "bt_soundbar": {"present": bool(bt), "paired": soundbar["paired"], "mac": soundbar["mac"], "label": soundbar["name"], "type": "bt", "name": BT_SOUNDBAR_SINK, "volume": _sink_volume(BT_SOUNDBAR_SINK) if bt else None, "state": bt.get("state") if bt else None},
            "usb_alexa_input": {"present": bool(usb_in), "type": "usb_input", "name": USB_ALEXA_SRC, "volume": _source_volume(USB_ALEXA_SRC) if usb_in else None, "state": usb_in.get("state") if usb_in else None},
            "dlna_output": {"present": bool(dlna_out), "type": "dlna_output", "name": dlna_out["name"] if dlna_out else None, "volume": _sink_volume(dlna_out["name"]) if dlna_out else None, "state": dlna_out.get("state") if dlna_out else None},
            "usb_output": {"present": bool(usb_out), "type": "usb_output", "name": usb_out["name"] if usb_out else None, "volume": _sink_volume(usb_out["name"]) if usb_out else None, "state": usb_out.get("state") if usb_out else None},
        },
        "routes": {"alexa_to_bt": {"on": bool(loop_id), "module_id": loop_id, "ready": bool(bt and usb_in), "missing": {"bt_soundbar": not bool(bt), "usb_alexa_input": not bool(usb_in)}}},
        "bluetooth": {"soundbar": soundbar},
        "latency": latency,
        "paired_bt": paired,
        "dlna_connected": _pa_dlna_running(),
        "keepalive": _keepalive_status(),
    }


def audio_state(force: bool = False) -> Dict[str, Any]:
    """Return cached audio state briefly to avoid repeated pactl/bluetooth pressure."""
    now = time.monotonic()
    with _audio_state_lock:
        cached = _audio_state_cache.get("data")
        if (not force) and cached is not None and now - _audio_state_cache.get("ts", 0) < AUDIO_STATE_CACHE_TTL:
            data = json.loads(json.dumps(cached))
            data["cache"] = {"hit": True, "ttl_ms": int(AUDIO_STATE_CACHE_TTL * 1000)}
            return data
        data = _audio_state_uncached()
        _audio_state_cache["ts"] = time.monotonic()
        _audio_state_cache["data"] = json.loads(json.dumps(data))
        data["cache"] = {"hit": False, "ttl_ms": int(AUDIO_STATE_CACHE_TTL * 1000)}
        return data


def _pa_dlna_running() -> bool:
    """Check if PulseAudio DLNA is running."""
    try:
        r = _run(["pactl", "list", "short", "modules"])
        return "module-null-sink" in r.stdout and "dlna" in r.stdout.lower()
    except Exception:
        return False

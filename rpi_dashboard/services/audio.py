"""Audio service module for RPi-TV Dashboard.

Handles audio routing, mixer, DLNA, Bluetooth audio, and PipeWire/PulseAudio integration.
"""

import json
import os
import re
import subprocess
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

# Constants
AUDIO_LATENCY_FILE = os.path.expanduser("~/rpi-dashboard/.audio-latency.json")
_DLNAIN_MODE_FILE = os.path.expanduser("~/rpi-dashboard/.dlnain-mode.json")
AUDIO_STATE_CACHE_TTL = 0.75
SILENT_WAV = "silent-48k.wav"

# Device names (from config or hardcoded for now)
BT_SOUNDBAR_SINK = "bluez_output.00_00_00_00_00_00.a2dp_sink"
BT_SOUNDBAR_MAC = "00:00:00:00:00:00"
BT_SOUNDBAR_NAME = "Soundbar"
HDMI_SINK = "alsa_output.platform-hdmi-audio.0.hdmi-stereo"
USB_ALEXA_SRC = "usb-Audio_Alexa_Input-00.analog-stereo"
DLNA_SINK_KEYWORDS = ["gmrender", "gmediarender", "dlna"]

# Cache
_audio_state_cache: Dict[str, Any] = {}
_audio_state_lock = threading.Lock()


def _run(cmd: List[str], t: float = 5) -> subprocess.CompletedProcess:
    """Run a command with timeout."""
    return subprocess.run(cmd, capture_output=True, text=True, timeout=t)


def _parse_int(value: Any, field: str) -> Tuple[Optional[int], Optional[Dict]]:
    """Parse integer from value, return error dict if failed."""
    try:
        return int(str(value).strip()), None
    except (TypeError, ValueError):
        return None, {"ok": False, "error": f"{field} must be an integer"}


def _pactl_lines(kind: str) -> List[Dict[str, str]]:
    """Get pactl list short output parsed into dicts."""
    r = _run(["pactl", "list", "short", kind])
    out = []
    for l in r.stdout.strip().split("\n"):
        if not l.strip():
            continue
        p = l.split("\t")
        if len(p) < 5:
            continue
        out.append({"id": p[0].strip(), "name": p[1].strip(), "state": p[-1].strip()})
    return out


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


def _loopback_module_id() -> Optional[str]:
    """Find Alexa-to-BT loopback module ID."""
    try:
        r = _run(["pactl", "list", "short", "modules"])
        for l in r.stdout.splitlines():
            if "module-loopback" in l and USB_ALEXA_SRC in l and BT_SOUNDBAR_SINK in l:
                return l.split()[0]
    except Exception as e:
        print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    return None


def _find_loopback_by_source(source_name: str) -> Optional[str]:
    """Find loopback module ID for a given source."""
    try:
        r = _run(["pactl", "list", "short", "modules"])
        for l in r.stdout.splitlines():
            if "module-loopback" in l and source_name in l:
                return l.split()[0]
    except Exception as e:
        print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    return None


def _find_loopbacks() -> List[Dict[str, Any]]:
    """Find all active loopback modules."""
    loops = []
    try:
        r = _run(["pactl", "list", "short", "modules"])
        for l in r.stdout.splitlines():
            if "module-loopback" in l:
                parts = l.split()
                mod_id = parts[0]
                m = re.search(r'source=(\S+)', l)
                src = m.group(1) if m else None
                m = re.search(r'sink=(\S+)', l)
                snk = m.group(1) if m else None
                loops.append({"id": mod_id, "source": src, "sink": snk})
    except Exception as e:
        print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    return loops


def _start_loopback(source: str, sink: str, rate: int = 48000, channels: int = 2) -> Optional[int]:
    """Start a PipeWire loopback from source to sink. Returns module ID."""
    r = _run(["pactl", "load-module", "module-loopback",
              f"source={source}", f"sink={sink}",
              f"rate={rate}", f"channels={channels}",
              "channel_map=front-left,front-right",
              "source_dont_move=true", "sink_dont_move=true",
              "latency_msec=20", "remix=true"], t=10)
    if r.returncode == 0:
        try:
            return int(r.stdout.strip())
        except Exception as e:
            print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    return None


def _stop_loopback(module_id: str) -> bool:
    """Stop a specific loopback module."""
    if not module_id:
        return False
    r = _run(["pactl", "unload-module", str(module_id)], t=5)
    return r.returncode == 0


def _stop_loopback_by_source(source_name: str) -> bool:
    """Stop loopback(s) for a given source."""
    stopped = False
    for lb in _find_loopbacks():
        if lb["source"] == source_name:
            if _stop_loopback(lb["id"]):
                stopped = True
    return stopped


def _get_default_sink() -> Optional[str]:
    """Get current default sink."""
    try:
        return _run(["pactl", "get-default-sink"]).stdout.strip()
    except Exception:
        return None


def _resolve_alexa_target() -> Optional[str]:
    """Determine where Alexa AUX should route based on default sink."""
    ds = _get_default_sink()
    if ds and ds not in ("", "none"):
        return ds
    sinks = _pactl_lines("sinks")
    names = [s["name"] for s in sinks]
    for candidate in [BT_SOUNDBAR_SINK] + [n for n in names if any(k in n for k in DLNA_SINK_KEYWORDS)] + [HDMI_SINK]:
        if candidate in names:
            return candidate
    return names[0] if names else None


def _load_dlnain_mode() -> Dict[str, Any]:
    """Load DLNA input mode from file."""
    try:
        with open(_DLNAIN_MODE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"mode": "follow", "manual_sink": None}


def _save_dlnain_mode(data: Dict[str, Any]) -> None:
    """Save DLNA input mode to file."""
    try:
        with open(_DLNAIN_MODE_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)


def _resolve_dlnain_target() -> Optional[str]:
    """Determine DLNA Input target based on mode."""
    cfg = _load_dlnain_mode()
    if cfg.get("mode") == "manual" and cfg.get("manual_sink"):
        return cfg["manual_sink"]
    return _resolve_alexa_target()


def _dlnain_loopback_running() -> Tuple[bool, Optional[str]]:
    """Check if DLNA Input loopback (gmrender source) is active."""
    gmrender_src = None
    try:
        r = _run(["pactl", "list", "short", "sources"])
        for l in r.stdout.splitlines():
            if "gmediarender" in l.lower() or "gmrender" in l.lower():
                parts = l.split()
                if len(parts) >= 2:
                    gmrender_src = parts[1]
    except Exception as e:
        print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    if not gmrender_src:
        return False, None
    lb = _find_loopback_by_source(gmrender_src)
    return lb is not None, gmrender_src


def _alexa_loopback_running() -> Tuple[bool, Optional[str], Optional[str]]:
    """Check if Alexa AUX loopback is active."""
    try:
        r = _run(["pactl", "list", "short", "modules"])
        for l in r.stdout.splitlines():
            if "module-loopback" in l and USB_ALEXA_SRC in l:
                m = re.search(r'sink=(\S+)', l)
                target = m.group(1) if m else None
                m2 = re.search(r'^(\d+)', l)
                mod_id = m2.group(1) if m2 else None
                return True, target, mod_id
    except Exception as e:
        print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    return False, None, None


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


def _load_audio_latency() -> Dict[str, int]:
    """Load audio latency settings."""
    try:
        if os.path.exists(AUDIO_LATENCY_FILE):
            with open(AUDIO_LATENCY_FILE) as f:
                return json.load(f)
    except Exception as e:
        print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)
    return {"dlna_output_offset_ms": 0, "default_latency_ms": 0}


def _save_audio_latency(data: Dict[str, int]) -> None:
    """Save audio latency settings."""
    try:
        with open(AUDIO_LATENCY_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)


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


def _audio_state_uncached() -> Dict[str, Any]:
    """Get audio state without cache."""
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


def get_audio_matrix() -> Dict[str, Any]:
    """Get PipeWire audio matrix (nodes and links)."""
    try:
        d = json.loads(subprocess.run(["pw-dump"], capture_output=True, timeout=5).stdout)
    except Exception:
        return {"nodes": {}, "links": []}

    nodes = {}
    for obj in d:
        if obj.get("type") == "PipeWire:Interface:Node":
            nid = obj.get("id")
            props = obj.get("info", {}).get("props", {})
            name = props.get("node.name", "")
            desc = props.get("node.description", name)
            klass = props.get("media.class", "")
            if "Audio" in klass:
                nodes[nid] = {"id": nid, "name": name, "desc": desc, "class": klass}

    links = set()
    for obj in d:
        if obj.get("type") == "PipeWire:Interface:Link":
            info = obj.get("info", {})
            if info.get("output-node-id") and info.get("input-node-id"):
                links.add((info.get("output-node-id"), info.get("input-node-id")))

    # Add synthetic links for module-loopback
    try:
        r_mod = subprocess.run(["pactl", "list", "short", "modules"], capture_output=True, text=True, timeout=2)
        for line in r_mod.stdout.splitlines():
            if "module-loopback" in line and "source=" in line and "sink=" in line:
                parts = line.split()
                src_name = next((p.split("=")[1] for p in parts if p.startswith("source=")), None)
                snk_name = next((p.split("=")[1] for p in parts if p.startswith("sink=")), None)
                src_id = next((n["id"] for n in nodes.values() if n["name"] == src_name), None)
                snk_id = next((n["id"] for n in nodes.values() if n["name"] == snk_name), None)
                if src_id and snk_id:
                    links.add((src_id, snk_id))
    except Exception:
        pass

    return {"nodes": nodes, "links": list(links)}


def audio_matrix_link(out_n: str, in_n: str, state: str) -> Dict[str, Any]:
    """Link or unlink audio nodes in the matrix."""
    is_dlna = "-uuid:" in in_n

    if is_dlna:
        if state == "1":
            r = subprocess.run(["pactl", "list", "short", "modules"], capture_output=True, text=True)
            if f"source={out_n}" in r.stdout and f"sink={in_n}" in r.stdout:
                return {"ok": True, "out": "already linked via loopback"}
            cmd = ["pactl", "load-module", "module-loopback", f"source={out_n}", f"sink={in_n}"]
            r = subprocess.run(cmd, capture_output=True, text=True)
            return {"ok": r.returncode == 0, "out": r.stdout.strip()[:200]}
        else:
            r = subprocess.run(["pactl", "list", "short", "modules"], capture_output=True, text=True)
            unloaded = False
            for line in r.stdout.splitlines():
                if "module-loopback" in line and f"source={out_n}" in line and f"sink={in_n}" in line:
                    mod_id = line.split()[0]
                    subprocess.run(["pactl", "unload-module", mod_id])
                    unloaded = True
            return {"ok": True, "out": "unloaded" if unloaded else "not found"}

    cmd = ["pw-link", out_n, in_n] if state == "1" else ["pw-link", "-d", out_n, in_n]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=1.5)
        out_str = (r.stdout + r.stderr).strip()
        ok = (r.returncode == 0) or ("File exists" in out_str and state == "1")
        return {"ok": ok, "out": out_str[:200]}
    except subprocess.TimeoutExpired:
        return {"ok": True, "out": "already linked"}


def audio_set_volume(kind: str, name: str, volume: int) -> Dict[str, Any]:
    """Set volume for sink or source."""
    vol = max(0, min(150, volume))
    cmd = ["pactl", "set-" + kind + "-volume", name, str(vol) + "%"]
    r = _run(cmd, t=5)

    # Propagate volume to sink inputs when adjusting sink volume
    if kind == "sink":
        try:
            sinks = _run(["pactl", "list", "short", "sinks"]).stdout.splitlines()
            sink_id = None
            for line in sinks:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == name:
                    sink_id = parts[0]
                    break
            if sink_id:
                inputs = _run(["pactl", "list", "short", "sink-inputs"]).stdout.splitlines()
                for line in inputs:
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] == sink_id:
                        input_id = parts[0]
                        _run(["pactl", "set-sink-input-volume", input_id, str(vol) + "%"], t=3)
        except Exception:
            pass

    return {"ok": r.returncode == 0, "volume": vol}


def audio_set_default(name: str) -> Dict[str, Any]:
    """Set default audio sink."""
    r = _run(["pactl", "set-default-sink", name], t=5)
    return {"ok": r.returncode == 0}


def _apply_dlna_delay() -> None:
    """Apply DLNA audio delay offset."""
    try:
        latency = _load_audio_latency()
        offset = latency.get("dlna_output_offset_ms", 0)
        if offset != 0:
            # Apply delay to DLNA sink
            pass  # TODO: Implement actual delay application
    except Exception as e:
        print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)


def _reset_dlna_delay() -> None:
    """Reset DLNA audio delay."""
    try:
        latency = _load_audio_latency()
        latency["dlna_output_offset_ms"] = 0
        _save_audio_latency(latency)
    except Exception as e:
        print(f"[WARN] Swallowed exception: {type(e).__name__}: {e}", file=sys.stderr)


def audio_set_latency(key: str, value_ms: int) -> Dict[str, Any]:
    """Set audio latency value."""
    latency = _load_audio_latency()
    latency[key] = value_ms
    _save_audio_latency(latency)
    _apply_dlna_delay()
    return {"ok": True, "latency": latency}


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


def diagnose_bt_audio_stutter() -> Dict[str, Any]:
    """Diagnose Bluetooth audio stutter issues.
    
    Returns diagnostic information about:
    - PipeWire buffer settings
    - Wi-Fi/BT frequency overlap
    - A2DP profile configuration
    """
    diagnostics: Dict[str, Any] = {
        "pipewire_quantum": None,
        "pipewire_rate": None,
        "wifi_frequency": None,
        "bt_frequency": None,
        "frequency_overlap": False,
        "recommendations": []
    }
    
    try:
        # Check PipeWire quantum settings
        r = _run(["pw-metadata", "-n", "settings"], t=3)
        if r.returncode == 0:
            for line in r.stdout.splitlines():
                if "quantum" in line.lower():
                    try:
                        diagnostics["pipewire_quantum"] = int(line.split("=")[1].strip())
                    except Exception:
                        pass
                if "rate" in line.lower() and "48000" in line:
                    diagnostics["pipewire_rate"] = 48000
    except Exception:
        pass
    
    try:
        # Check Wi-Fi frequency
        r = _run(["iwconfig", "wlan0"], t=3)
        if r.returncode == 0:
            output = r.stdout.lower()
            if "2.4ghz" in output or "2412" in output or "2437" in output:
                diagnostics["wifi_frequency"] = "2.4ghz"
            elif "5ghz" in output or "5180" in output or "5240" in output:
                diagnostics["wifi_frequency"] = "5ghz"
    except Exception:
        pass
    
    # BT typically uses 2.4GHz
    diagnostics["bt_frequency"] = "2.4ghz"
    
    # Check for frequency overlap
    if diagnostics["wifi_frequency"] == "2.4ghz" and diagnostics["bt_frequency"] == "2.4ghz":
        diagnostics["frequency_overlap"] = True
        diagnostics["recommendations"].append(
            "Wi-Fi and Bluetooth both use 2.4GHz band. Consider:"
        )
        diagnostics["recommendations"].append(
            "1. Connect to 5GHz Wi-Fi network"
        )
        diagnostics["recommendations"].append(
            "2. Increase PipeWire quantum to 1024"
        )
        diagnostics["recommendations"].append(
            "3. Use wired Ethernet instead of Wi-Fi"
        )
    
    if diagnostics["pipewire_quantum"] and diagnostics["pipewire_quantum"] < 512:
        diagnostics["recommendations"].append(
            f"Current quantum ({diagnostics['pipewire_quantum']}) is low. Try 1024."
        )
    
    return diagnostics


def fix_bt_audio_stutter() -> Dict[str, Any]:
    """Apply fixes for Bluetooth audio stutter.
    
    Attempts to:
    1. Increase PipeWire quantum to 1024
    2. Set appropriate buffer size
    """
    fixes_applied = []
    
    try:
        # Increase PipeWire quantum
        r = _run(["pw-metadata", "-n", "settings", "0", "quantum", "1024"], t=3)
        if r.returncode == 0:
            fixes_applied.append("Set PipeWire quantum to 1024")
    except Exception:
        pass
    
    try:
        # Set rate to 48000
        r = _run(["pw-metadata", "-n", "settings", "0", "rate", "48000"], t=3)
        if r.returncode == 0:
            fixes_applied.append("Set PipeWire rate to 48000")
    except Exception:
        pass
    
    return {
        "ok": len(fixes_applied) > 0,
        "fixes_applied": fixes_applied,
        "diagnostics": diagnose_bt_audio_stutter()
    }


def _pa_dlna_running() -> bool:
    """Check if PulseAudio DLNA is running."""
    try:
        r = _run(["pactl", "list", "short", "modules"])
        return "module-null-sink" in r.stdout and "dlna" in r.stdout.lower()
    except Exception:
        return False


def audio_select_dlna_renderer(name: str, location: str, usn: str = "") -> Dict[str, Any]:
    """Select a DLNA renderer for audio output."""
    # TODO: Implement DLNA renderer selection
    return {"ok": True, "renderer": name}


def dlna_renderer_status() -> Dict[str, Any]:
    """Get DLNA renderer status."""
    running = _pa_dlna_running()
    return {"running": running}


def dlna_renderer_start() -> Dict[str, Any]:
    """Start DLNA renderer."""
    # TODO: Implement DLNA renderer start
    return {"ok": True}


def dlna_renderer_stop() -> Dict[str, Any]:
    """Stop DLNA renderer."""
    # TODO: Implement DLNA renderer stop
    return {"ok": True}

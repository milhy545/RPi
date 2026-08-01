import json
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional


from .common import _run, USB_ALEXA_SRC, BT_SOUNDBAR_SINK, MULTI_OUTPUT_SINK

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

def _find_multi_output_module() -> Optional[Dict[str, Any]]:
    """Find the dashboard-owned Bluetooth combine sink module."""
    try:
        r = _run(["pactl", "list", "short", "modules"])
        for line in r.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) < 2 or parts[1] != "module-combine-sink":
                continue
            if f"sink_name={MULTI_OUTPUT_SINK}" not in line:
                continue
            slaves_match = re.search(r"(?:^|\s)slaves=([^\s]+)", line)
            slaves = slaves_match.group(1).split(",") if slaves_match else []
            return {"id": parts[0], "slaves": slaves}
    except Exception as e:
        print(f"[WARN] Multi-output module lookup failed: {type(e).__name__}: {e}", file=sys.stderr)
    return None

def _find_loopback(source: str, sink: str) -> Optional[str]:
    """Find one loopback that connects an exact source and sink."""
    for loopback in _find_loopbacks():
        if loopback.get("source") == source and loopback.get("sink") == sink:
            return str(loopback["id"])
    return None

def _start_loopback(source: str, sink: str, rate: int = 48000, channels: int = 2) -> Optional[int]:
    """Start a PipeWire loopback from source to sink. Returns module ID."""
    r = _run(["pactl", "load-module", "module-loopback",
              f"source={source}", f"sink={sink}",
              f"rate={rate}", f"channels={channels}",
              "channel_map=front-left,front-right",
              "source_dont_move=true", "sink_dont_move=true",
              "remix=true"], t=10)
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
    if state == "1":
        # Check if loopback module is already loaded
        r = subprocess.run(["pactl", "list", "short", "modules"], capture_output=True, text=True)
        if f"source={out_n}" in r.stdout and f"sink={in_n}" in r.stdout:
            return {"ok": True, "out": "already linked via loopback"}

        # Try loading module-loopback for reliable audio routing between source & sink nodes
        cmd = ["pactl", "load-module", "module-loopback", f"source={out_n}", f"sink={in_n}"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            return {"ok": True, "out": f"loopback module loaded: {r.stdout.strip()[:200]}"}

        # Fallback to direct pw-link for raw PipeWire port-level connections
        cmd = ["pw-link", out_n, in_n]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=2.0)
            out_str = (r.stdout + r.stderr).strip()
            ok = (r.returncode == 0) or ("File exists" in out_str)
            return {"ok": ok, "out": out_str[:200]}
        except subprocess.TimeoutExpired:
            return {"ok": True, "out": "already linked"}
    else:
        # Unlink: unload matching module-loopback if present
        unloaded = False
        r = subprocess.run(["pactl", "list", "short", "modules"], capture_output=True, text=True)
        for line in r.stdout.splitlines():
            if "module-loopback" in line and f"source={out_n}" in line and f"sink={in_n}" in line:
                mod_id = line.split()[0]
                subprocess.run(["pactl", "unload-module", mod_id], capture_output=True, text=True)
                unloaded = True

        # Also try pw-link -d for direct port connections
        cmd = ["pw-link", "-d", out_n, in_n]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=2.0)
            out_str = (r.stdout + r.stderr).strip()
            pw_ok = (r.returncode == 0)
        except subprocess.TimeoutExpired:
            pw_ok = True
            out_str = "unlinked"

        return {"ok": unloaded or pw_ok, "out": "unloaded" if unloaded else out_str[:200]}

__all__ = [
    "_loopback_module_id",
    "_find_loopback_by_source",
    "_find_loopbacks",
    "_find_multi_output_module",
    "_find_loopback",
    "_start_loopback",
    "_stop_loopback",
    "_stop_loopback_by_source",
    "get_audio_matrix",
    "audio_matrix_link"
]


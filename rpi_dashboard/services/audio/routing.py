import json
import re
import sys
from typing import Any, Dict, Optional, Tuple

from .common import (
    _run, _pactl_lines, _DLNAIN_MODE_FILE, USB_ALEXA_SRC, BT_SOUNDBAR_SINK,
    DLNA_SINK_KEYWORDS, HDMI_SINK
)
from .state import _get_default_sink
from .matrix import _find_loopback_by_source

__all__ = [
    "_resolve_alexa_target",
    "_load_dlnain_mode",
    "_save_dlnain_mode",
    "_resolve_dlnain_target",
    "_dlnain_loopback_running",
    "_alexa_loopback_running",
]


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

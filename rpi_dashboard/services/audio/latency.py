import json
import os
import sys
from typing import Any, Dict

from .common import AUDIO_LATENCY_FILE

__all__ = [
    "_load_audio_latency",
    "_save_audio_latency",
    "_apply_dlna_delay",
    "_reset_dlna_delay",
    "audio_set_latency",
]


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

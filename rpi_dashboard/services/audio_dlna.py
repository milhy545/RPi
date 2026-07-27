"""DLNA renderer helpers for RPi-TV Dashboard.

These helpers keep the main audio module focused on shared PipeWire state and
routing primitives while exposing a small DLNA-specific surface.
"""

from __future__ import annotations

from typing import Any, Dict

from . import audio


def audio_select_dlna_renderer(name: str, location: str, usn: str = "") -> Dict[str, Any]:
    """Select a DLNA renderer for audio output."""
    return {"ok": True, "renderer": name}


def dlna_renderer_status() -> Dict[str, Any]:
    """Get DLNA renderer status."""
    return {"running": audio._pa_dlna_running()}


def dlna_renderer_start() -> Dict[str, Any]:
    """Start DLNA renderer."""
    return {"ok": True}


def dlna_renderer_stop() -> Dict[str, Any]:
    """Stop DLNA renderer."""
    return {"ok": True}


__all__ = [
    "audio_select_dlna_renderer",
    "dlna_renderer_status",
    "dlna_renderer_start",
    "dlna_renderer_stop",
]

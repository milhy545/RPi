from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DisplayItem:
    primary: str
    detail: str
    status: str = ""


def badge(value: str) -> str:
    clean = "".join(ch for ch in value.upper() if ch.isalnum() or ch in {"_", "-"})
    return f"[{clean}]"


def truncate_middle(value: str, max_len: int) -> str:
    if len(value) <= max_len:
        return value
    if max_len < 8:
        return value[:max_len]
    suffix = value.rsplit(".", 1)[-1]
    right = len(suffix) if len(suffix) <= max_len - 8 else (max_len - 3) // 2
    left = max_len - 3 - right
    return f"{value[:left]}...{value[-right:]}"


def human_audio_sink(sink_id: str, *, default: bool = False) -> DisplayItem:
    lowered = sink_id.lower()
    if "hdmi" in lowered:
        primary = "TV HDMI"
    elif "bluez" in lowered:
        primary = "Bluetooth Audio"
    elif "usb" in lowered:
        primary = "USB Audio"
    elif "dlna" in lowered or "lg_tv" in lowered or "windows_digital_media_renderer" in lowered:
        primary = "DLNA Renderer"
    else:
        primary = "Audio Output"
    return DisplayItem(primary=primary, detail=truncate_middle(sink_id, 44), status=badge("active") if default else "")


def human_bt_device(line: str, *, connected: bool = False, paired: bool = True) -> DisplayItem:
    parts = line.split(None, 2)
    mac = parts[1] if len(parts) >= 2 else "unknown"
    name = parts[2] if len(parts) >= 3 else "Unknown Bluetooth Device"
    state = "connected" if connected else ("paired" if paired else "found")
    return DisplayItem(primary=name, detail=mac, status=badge(state))

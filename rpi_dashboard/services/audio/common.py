
import os


import subprocess


import threading



from typing import Any, Dict, List, Optional, Tuple

from rpi_dashboard.services.audio_diagnostics import (
    diagnose_bt_audio_stutter as diagnose_bt_audio_stutter,
    fix_bt_audio_stutter as fix_bt_audio_stutter,
)

AUDIO_LATENCY_FILE = os.path.expanduser("~/rpi-dashboard/.audio-latency.json")

_DLNAIN_MODE_FILE = os.path.expanduser("~/rpi-dashboard/.dlnain-mode.json")

AUDIO_STATE_CACHE_TTL = 0.75

SILENT_WAV = "silent-48k.wav"

MULTI_OUTPUT_SINK = "rpi_bt_multi_output"

MULTI_OUTPUT_STATE_FILE = os.path.expanduser(
    os.environ.get(
        "RPI_BLUETOOTH_MULTI_OUTPUT_STATE_PATH",
        "~/.config/rpi-dashboard/bluetooth-multi-output.json",
    )
)

BT_SOUNDBAR_SINK = "bluez_output.00_00_00_00_00_00.a2dp_sink"

BT_SOUNDBAR_MAC = "00:00:00:00:00:00"

BT_SOUNDBAR_NAME = "Soundbar"

HDMI_SINK = "alsa_output.platform-hdmi-audio.0.hdmi-stereo"

USB_ALEXA_SRC = "usb-Audio_Alexa_Input-00.analog-stereo"

DLNA_SINK_KEYWORDS = ["gmrender", "gmediarender", "dlna"]

_audio_state_cache: Dict[str, Any] = {}

_audio_state_lock = threading.Lock()

_multi_output_lock = threading.RLock()

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
        out.append({
            "id": p[0].strip(),
            "name": p[1].strip(),
            "driver": p[2].strip(),
            "sample_spec": p[3].strip(),
            "state": p[-1].strip(),
        })
    return out

__all__ = [
    "AUDIO_LATENCY_FILE",
    "_DLNAIN_MODE_FILE",
    "AUDIO_STATE_CACHE_TTL",
    "SILENT_WAV",
    "MULTI_OUTPUT_SINK",
    "MULTI_OUTPUT_STATE_FILE",
    "BT_SOUNDBAR_SINK",
    "BT_SOUNDBAR_MAC",
    "BT_SOUNDBAR_NAME",
    "HDMI_SINK",
    "USB_ALEXA_SRC",
    "DLNA_SINK_KEYWORDS",
    "_audio_state_cache",
    "_audio_state_lock",
    "_multi_output_lock",
    "_run",
    "_parse_int",
    "_pactl_lines"
]


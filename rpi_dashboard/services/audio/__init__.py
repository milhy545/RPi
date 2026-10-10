"""Audio service module for RPi-TV Dashboard.

Handles audio routing, mixer, DLNA, Bluetooth audio, and PipeWire/PulseAudio integration.

This package re-exports all symbols from its submodules for backward compatibility.
Consumers can import directly: `from rpi_dashboard.services.audio import get_sinks`
"""

from rpi_dashboard.services.audio.common import *  # noqa: F401,F403
from rpi_dashboard.services.audio.profiles import *  # noqa: F401,F403
from rpi_dashboard.services.audio.mixer import *  # noqa: F401,F403
from rpi_dashboard.services.audio.keepalive import *  # noqa: F401,F403
from rpi_dashboard.services.audio.latency import *  # noqa: F401,F403
from rpi_dashboard.services.audio.matrix import *  # noqa: F401,F403
from rpi_dashboard.services.audio.multi_output import *  # noqa: F401,F403
from rpi_dashboard.services.audio.state import *  # noqa: F401,F403
from rpi_dashboard.services.audio.routing import *  # noqa: F401,F403
from rpi_dashboard.services.audio_diagnostics import (
    diagnose_bt_audio_stutter as diagnose_bt_audio_stutter,
    fix_bt_audio_stutter as fix_bt_audio_stutter,
)

"""Safety boundary for optional outbound Bluetooth HID control."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def hid_transport_status() -> dict[str, Any]:
    """Report prerequisites without loading modules or registering a profile."""
    uhid = Path("/dev/uhid").exists()
    profile_active = os.environ.get("RPI_BLUETOOTH_HID_PROFILE_ACTIVE") == "1"
    blockers = []
    if not uhid:
        blockers.append("/dev/uhid is unavailable")
    if not profile_active:
        blockers.append("Outbound BlueZ HID profile is not explicitly registered")
    return {
        "available": uhid and profile_active,
        "enabled_by_default": False,
        "uhid": uhid,
        "profile_active": profile_active,
        "blockers": blockers,
        "safe_alternative": "Use AVRCP for media keys when the remote player advertises it",
    }

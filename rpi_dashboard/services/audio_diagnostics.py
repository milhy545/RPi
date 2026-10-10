"""Audio diagnostics helpers for RPi-TV Dashboard.

Bluetooth stutter checks and fixes live here so the main audio service can stay
focused on routing and state management.
"""

from __future__ import annotations

import re
from typing import Any, Dict

from . import audio


def diagnose_bt_audio_stutter() -> Dict[str, Any]:
    """Diagnose Bluetooth audio stutter issues."""
    diagnostics: Dict[str, Any] = {
        "pipewire_quantum": None,
        "pipewire_rate": None,
        "wifi_frequency": None,
        "bt_frequency": None,
        "frequency_overlap": False,
        "recommendations": [],
    }

    try:
        result = audio._run(["pw-metadata", "-n", "settings"], t=3)
        if result.returncode == 0:
            quantum = re.search(r"key:'clock\.quantum'\s+value:'(\d+)'", result.stdout)
            rate = re.search(r"key:'clock\.rate'\s+value:'(\d+)'", result.stdout)
            if quantum:
                diagnostics["pipewire_quantum"] = int(quantum.group(1))
            if rate:
                diagnostics["pipewire_rate"] = int(rate.group(1))
    except Exception:
        pass

    try:
        result = audio._run(["iw", "dev", "wlan0", "link"], t=3)
        if result.returncode == 0:
            output = result.stdout.lower()
            frequency = re.search(r"freq:\s*(\d+)", output)
            mhz = int(frequency.group(1)) if frequency else 0
            if 2400 <= mhz < 2500:
                diagnostics["wifi_frequency"] = "2.4ghz"
            elif 4900 <= mhz < 5900:
                diagnostics["wifi_frequency"] = "5ghz"
    except Exception:
        pass

    diagnostics["bt_frequency"] = "2.4ghz"

    if diagnostics["wifi_frequency"] == "2.4ghz" and diagnostics["bt_frequency"] == "2.4ghz":
        diagnostics["frequency_overlap"] = True
        diagnostics["recommendations"].extend(
            [
                "Wi-Fi and Bluetooth both use 2.4GHz band. Consider:",
                "1. Connect to 5GHz Wi-Fi network",
                "2. Keep PipeWire quantum at the measured stable baseline",
                "3. Use wired Ethernet instead of Wi-Fi",
            ]
        )

    if diagnostics["pipewire_quantum"] and diagnostics["pipewire_quantum"] < 1024:
        diagnostics["recommendations"].append(
            f"Current quantum ({diagnostics['pipewire_quantum']}) is low. Try 1024."
        )

    return diagnostics


def fix_bt_audio_stutter(*, apply: bool = False) -> Dict[str, Any]:
    """Plan conservative PipeWire baseline changes; mutate only with apply=True."""
    fixes_applied = []
    diagnostics = diagnose_bt_audio_stutter()
    planned = []
    if diagnostics.get("pipewire_quantum") is not None and diagnostics["pipewire_quantum"] < 1024:
        planned.append(("quantum", "1024", "Set PipeWire quantum to 1024"))
    if diagnostics.get("pipewire_rate") is not None and diagnostics["pipewire_rate"] != 48000:
        planned.append(("rate", "48000", "Set PipeWire rate to 48000"))
    if apply:
        for key, value, label in planned:
            try:
                result = audio._run(["pw-metadata", "-n", "settings", "0", key, value], t=3)
            except Exception:
                continue
            if result.returncode == 0:
                fixes_applied.append(label)
    return {
        "ok": True,
        "applied": apply,
        "fixes_applied": fixes_applied,
        "planned_fixes": [label for _, _, label in planned],
        "diagnostics": diagnostics,
        "next_step": (
            "Measure route-specific xruns, codec, and CPU load; the 1024/48000 baseline is already active."
            if not planned
            else "Apply only after reviewing the recorded baseline."
        ),
    }


__all__ = ["diagnose_bt_audio_stutter", "fix_bt_audio_stutter"]

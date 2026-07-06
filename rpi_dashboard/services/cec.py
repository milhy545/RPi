"""CEC service module for RPi-TV Dashboard.

Handles HDMI-CEC commands for TV control.
"""

import subprocess
import sys
from typing import Any, Dict, List, Optional


def _run(cmd, t=5):
    """Run a command with timeout."""
    return subprocess.run(cmd, capture_output=True, text=True, timeout=t)


def cec_cmd(cmd: str, timeout: float = 5) -> Dict[str, Any]:
    """Send a CEC command."""
    try:
        r = _run(["cec-client", "-d", "1", "-s"], t=timeout)
        # Send command via stdin
        proc = subprocess.Popen(
            ["cec-client", "-d", "1", "-s"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(input=cmd + "\n", timeout=timeout)
        return {"ok": proc.returncode == 0, "output": stdout.strip()[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def cec_scan() -> Dict[str, Any]:
    """Scan CEC bus for devices."""
    try:
        r = _run(["echo", "scan"], t=3)
        # Actually scan using cec-client
        proc = subprocess.Popen(
            ["cec-client", "-d", "1", "-s"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(input="scan\n", timeout=5)

        devices = []
        for line in stdout.split("\n"):
            if "device #" in line.lower():
                devices.append(line.strip())

        return {"ok": True, "devices": devices}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def cec_power_on() -> Dict[str, Any]:
    """Turn on TV via CEC."""
    return cec_cmd("on 0")


def cec_power_off() -> Dict[str, Any]:
    """Turn off TV via CEC."""
    return cec_cmd("standby 0")


def cec_volume_up() -> Dict[str, Any]:
    """Increase volume via CEC."""
    return cec_cmd("volup")


def cec_volume_down() -> Dict[str, Any]:
    """Decrease volume via CEC."""
    return cec_cmd("voldown")


def cec_mute() -> Dict[str, Any]:
    """Toggle mute via CEC."""
    return cec_cmd("mute")


def cec_up() -> Dict[str, Any]:
    """Navigate up via CEC."""
    return cec_cmd("up")


def cec_down() -> Dict[str, Any]:
    """Navigate down via CEC."""
    return cec_cmd("down")


def cec_left() -> Dict[str, Any]:
    """Navigate left via CEC."""
    return cec_cmd("left")


def cec_right() -> Dict[str, Any]:
    """Navigate right via CEC."""
    return cec_cmd("right")


def cec_select() -> Dict[str, Any]:
    """Select/OK via CEC."""
    return cec_cmd("select")


def cec_back() -> Dict[str, Any]:
    """Go back via CEC."""
    return cec_cmd("back")


def cec_menu() -> Dict[str, Any]:
    """Open menu via CEC."""
    return cec_cmd("menu")


def cec_input_hdmi1() -> Dict[str, Any]:
    """Switch to HDMI 1."""
    return cec_cmd("input 1")


def cec_input_hdmi2() -> Dict[str, Any]:
    """Switch to HDMI 2."""
    return cec_cmd("input 2")


def cec_input_hdmi3() -> Dict[str, Any]:
    """Switch to HDMI 3."""
    return cec_cmd("input 3")


def cec_active_source() -> Dict[str, Any]:
    """Set RPi as active source."""
    return cec_cmd("active_source")


def cec_physical_address() -> Optional[str]:
    """Get physical address of the TV."""
    try:
        proc = subprocess.Popen(
            ["cec-client", "-d", "1", "-s"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(input="tx 0f 82 10 00\n", timeout=3)
        # Parse response
        for line in stdout.split("\n"):
            if "physical address" in line.lower():
                return line.split(":")[-1].strip()
        return None
    except Exception:
        return None

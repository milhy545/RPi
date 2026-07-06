"""Devices service module for RPi-TV Dashboard.

Handles Bluetooth, WiFi, and device management.
"""

import subprocess
import sys
from typing import Any, Dict, List, Optional


def _run(cmd, t=5):
    """Run a command with timeout."""
    return subprocess.run(cmd, capture_output=True, text=True, timeout=t)


def devices_state() -> Dict[str, Any]:
    """Get current devices state."""
    bt_paired = _bt_paired_devices()
    bt_scanned = _bt_scanned_devices()
    wifi = wifi_status()

    return {
        "bluetooth": {
            "paired": bt_paired,
            "scanned": bt_scanned,
        },
        "wifi": wifi,
    }


def _bt_paired_devices() -> List[Dict[str, str]]:
    """Get list of paired Bluetooth devices."""
    try:
        r = _run(["bluetoothctl", "devices", "Paired"], t=5)
        devices = []
        for line in r.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split(maxsplit=2)
            if len(parts) >= 3:
                devices.append({
                    "mac": parts[1],
                    "name": parts[2],
                    "type": _bt_device_type(parts[2]),
                })
        return devices
    except Exception as e:
        print(f"[WARN] BT paired devices error: {e}", file=sys.stderr)
        return []


def _bt_scanned_devices() -> List[Dict[str, str]]:
    """Get list of scanned Bluetooth devices."""
    try:
        r = _run(["bluetoothctl", "devices", "Scanned"], t=5)
        devices = []
        for line in r.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split(maxsplit=2)
            if len(parts) >= 3:
                devices.append({
                    "mac": parts[1],
                    "name": parts[2],
                    "type": _bt_device_type(parts[2]),
                })
        return devices
    except Exception as e:
        print(f"[WARN] BT scanned devices error: {e}", file=sys.stderr)
        return []


def _bt_device_type(name: str) -> str:
    """Determine device type from name."""
    name_lower = name.lower()
    if any(x in name_lower for x in ["speaker", "soundbar", "headphone", "earbuds"]):
        return "audio_output"
    if any(x in name_lower for x in ["controller", "gamepad", "xbox"]):
        return "gamepad"
    if any(x in name_lower for x in ["keyboard", "mouse"]):
        return "input"
    if any(x in name_lower for x in ["phone", "tablet"]):
        return "mobile"
    return "unknown"


def bluetooth_scan_devices(seconds: int = 5) -> Dict[str, Any]:
    """Scan for Bluetooth devices."""
    try:
        # Start discovery
        _run(["bluetoothctl", "scan", "on"], t=2)
        # Wait for scan
        import time
        time.sleep(seconds)
        # Stop discovery
        _run(["bluetoothctl", "scan", "off"], t=2)
        # Get scanned devices
        devices = _bt_scanned_devices()
        return {"ok": True, "devices": devices}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def bluetooth_pair(mac: str) -> Dict[str, Any]:
    """Pair with a Bluetooth device."""
    try:
        r = _run(["bluetoothctl", "pair", mac], t=10)
        return {"ok": r.returncode == 0, "output": r.stdout.strip()[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def bluetooth_trust(mac: str) -> Dict[str, Any]:
    """Trust a Bluetooth device."""
    try:
        r = _run(["bluetoothctl", "trust", mac], t=5)
        return {"ok": r.returncode == 0, "output": r.stdout.strip()[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def bluetooth_connect(mac: str) -> Dict[str, Any]:
    """Connect to a Bluetooth device."""
    try:
        r = _run(["bluetoothctl", "connect", mac], t=10)
        return {"ok": r.returncode == 0, "output": r.stdout.strip()[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def bluetooth_disconnect(mac: str) -> Dict[str, Any]:
    """Disconnect from a Bluetooth device."""
    try:
        r = _run(["bluetoothctl", "disconnect", mac], t=5)
        return {"ok": r.returncode == 0, "output": r.stdout.strip()[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def bluetooth_remove(mac: str) -> Dict[str, Any]:
    """Remove a Bluetooth device."""
    try:
        r = _run(["bluetoothctl", "remove", mac], t=5)
        return {"ok": r.returncode == 0, "output": r.stdout.strip()[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def wifi_status() -> Dict[str, Any]:
    """Get WiFi status."""
    try:
        # Check if NetworkManager is available
        r = _run(["nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL", "dev", "wifi"], t=5)
        if r.returncode != 0:
            return {"available": False, "connected": False}

        networks = []
        connected_ssid = None
        for line in r.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split(":")
            if len(parts) >= 3:
                active = parts[0] == "yes"
                ssid = parts[1]
                signal = int(parts[2]) if parts[2].isdigit() else 0
                networks.append({
                    "ssid": ssid,
                    "signal": signal,
                    "active": active,
                })
                if active:
                    connected_ssid = ssid

        return {
            "available": True,
            "connected": connected_ssid is not None,
            "connected_ssid": connected_ssid,
            "networks": networks,
        }
    except Exception as e:
        return {"available": False, "connected": False, "error": str(e)}


def wifi_scan() -> Dict[str, Any]:
    """Scan for WiFi networks."""
    try:
        r = _run(["nmcli", "dev", "wifi", "rescan"], t=10)
        if r.returncode != 0:
            return {"ok": False, "error": "Scan failed"}

        # Get scan results
        r2 = _run(["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi", "list"], t=5)
        networks = []
        seen = set()
        for line in r2.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split(":")
            if len(parts) >= 3:
                ssid = parts[0]
                if ssid and ssid not in seen:
                    seen.add(ssid)
                    networks.append({
                        "ssid": ssid,
                        "signal": int(parts[1]) if parts[1].isdigit() else 0,
                        "security": parts[2] if parts[2] else "none",
                    })

        return {"ok": True, "networks": networks}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def wifi_connect(ssid: str, password: str = "") -> Dict[str, Any]:
    """Connect to a WiFi network."""
    try:
        if password:
            cmd = ["nmcli", "dev", "wifi", "connect", ssid, "password", password]
        else:
            cmd = ["nmcli", "dev", "wifi", "connect", ssid]

        r = _run(cmd, t=15)
        return {"ok": r.returncode == 0, "output": r.stdout.strip()[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def wifi_disconnect() -> Dict[str, Any]:
    """Disconnect from WiFi."""
    try:
        r = _run(["nmcli", "dev", "disconnect", "wlan0"], t=5)
        return {"ok": r.returncode == 0, "output": r.stdout.strip()[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)}

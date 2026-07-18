"""Devices service module for RPi-TV Dashboard.

Handles Bluetooth, WiFi, and device management.
"""

import os
import shutil
import subprocess
import sys
from typing import Any, Dict, List

from .bluetooth import service as bluetooth_service


def _run(cmd, t=5):
    """Run a command with timeout."""
    return subprocess.run(cmd, capture_output=True, text=True, timeout=t)


def devices_state() -> Dict[str, Any]:
    """Get current devices state."""
    try:
        bluetooth = bluetooth_service.devices_compat_state()
    except Exception:
        bt_devices = bluetooth_devices()
        bt_paired = [d for d in bt_devices if d["paired"]]
        bt_scanned = [d for d in bt_devices if not d["paired"]]
        bluetooth = {
            "devices": bt_devices,
            "paired": bt_paired,
            "scanned": bt_scanned,
            "controller": bluetooth_controller_status(bt_devices),
        }
    wifi = wifi_status()

    return {
        "ok": True,
        "bluetooth": bluetooth,
        "wifi": wifi,
    }


def _bt_parse_devices(output: str) -> List[Dict[str, str]]:
    devices = []
    for line in output.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split(maxsplit=2)
        if len(parts) >= 3 and parts[0] == "Device":
            devices.append({
                "mac": parts[1],
                "name": parts[2],
            })
    return devices


def _bt_info(mac: str) -> Dict[str, bool]:
    try:
        r = _run(["bluetoothctl", "info", mac], t=5)
        info = r.stdout
        return {
            "paired": "Paired: yes" in info,
            "connected": "Connected: yes" in info,
            "trusted": "Trusted: yes" in info,
        }
    except Exception as e:
        print(f"[WARN] BT info error for {mac}: {e}", file=sys.stderr)
        return {"paired": False, "connected": False, "trusted": False}


def _bt_normalize(raw: Dict[str, str], *, paired_hint: bool = False) -> Dict[str, Any]:
    info = _bt_info(raw["mac"])
    kind = _bt_device_kind(raw["name"])
    return {
        "mac": raw["mac"],
        "name": raw["name"],
        "kind": kind,
        "type": _bt_device_type(raw["name"]),
        "paired": bool(info["paired"] or paired_hint),
        "connected": bool(info["connected"]),
        "trusted": bool(info["trusted"]),
    }


def _bt_list(scope: str) -> List[Dict[str, str]]:
    try:
        r = _run(["bluetoothctl", "devices", scope], t=5)
        return _bt_parse_devices(r.stdout)
    except Exception as e:
        print(f"[WARN] BT {scope.lower()} devices error: {e}", file=sys.stderr)
        return []


def bluetooth_devices() -> List[Dict[str, Any]]:
    """Return normalized paired and known scanned Bluetooth devices."""
    by_mac: Dict[str, Dict[str, Any]] = {}
    for raw in _bt_list("Paired"):
        by_mac[raw["mac"]] = _bt_normalize(raw, paired_hint=True)
    for raw in _bt_list("Scanned"):
        by_mac.setdefault(raw["mac"], _bt_normalize(raw, paired_hint=False))
    return sorted(
        by_mac.values(),
        key=lambda d: (not d["connected"], not d["paired"], d["kind"], d["name"].lower()),
    )


def _bt_paired_devices() -> List[Dict[str, Any]]:
    """Get list of paired Bluetooth devices."""
    try:
        return [_bt_normalize(raw, paired_hint=True) for raw in _bt_list("Paired")]
    except Exception as e:
        print(f"[WARN] BT paired devices error: {e}", file=sys.stderr)
        return []


def _bt_scanned_devices() -> List[Dict[str, Any]]:
    """Get list of scanned Bluetooth devices."""
    try:
        paired = {d["mac"] for d in _bt_paired_devices()}
        return [
            _bt_normalize(raw, paired_hint=False)
            for raw in _bt_list("Scanned")
            if raw["mac"] not in paired
        ]
    except Exception as e:
        print(f"[WARN] BT scanned devices error: {e}", file=sys.stderr)
        return []


def _bt_device_type(name: str) -> str:
    """Determine legacy device type from name."""
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


def _bt_device_kind(name: str) -> str:
    """Determine UI device role from name."""
    name_lower = name.lower()
    if "xbox" in name_lower or "x-box" in name_lower or "wireless controller" in name_lower:
        return "xbox_controller"
    if any(x in name_lower for x in ["controller", "gamepad", "joystick"]):
        return "gamepad"
    if any(x in name_lower for x in ["speaker", "soundbar", "headphone", "earbuds", "buds", "audio"]):
        return "speaker"
    if any(x in name_lower for x in ["keyboard", "mouse"]):
        return "input"
    if any(x in name_lower for x in ["phone", "tablet"]):
        return "mobile"
    return "unknown"


def _loaded_modules() -> List[str]:
    try:
        with open("/proc/modules", encoding="utf-8") as fh:
            return [line.split()[0] for line in fh if line.strip()]
    except OSError:
        return []


def _input_device_names() -> List[str]:
    try:
        with open("/proc/bus/input/devices", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return []
    names = []
    for line in text.splitlines():
        if line.startswith("N: Name="):
            names.append(line.split("=", 1)[1].strip().strip('"'))
    return names


def _ertm_state() -> Dict[str, Any]:
    path = "/sys/module/bluetooth/parameters/disable_ertm"
    if not os.path.exists(path):
        return {"available": False, "disabled": None, "value": None}
    try:
        with open(path, encoding="utf-8") as fh:
            value = fh.read().strip()
    except OSError as e:
        return {"available": True, "disabled": None, "value": None, "error": str(e)}
    return {"available": True, "disabled": value.lower() in {"1", "y", "yes", "true"}, "value": value}


def bluetooth_controller_status(devices: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    """Return Xbox/gamepad readiness hints for Steam Link."""
    bt_devices = devices if devices is not None else bluetooth_devices()
    controllers = [
        d for d in bt_devices
        if d.get("kind") in {"xbox_controller", "gamepad"} or d.get("type") == "gamepad"
    ]
    connected = [d for d in controllers if d.get("connected")]
    modules = _loaded_modules()
    module_state = {
        "xpadneo": "hid_xpadneo" in modules or "xpadneo" in modules,
        "xpad": "xpad" in modules,
        "uhid": "uhid" in modules,
        "hid_microsoft": "hid_microsoft" in modules,
    }
    inputs = [
        name for name in _input_device_names()
        if any(token in name.lower() for token in ("xbox", "controller", "gamepad"))
    ]
    steamlink = shutil.which("steamlink")
    return {
        "controllers": controllers,
        "connected": connected,
        "ertm": _ertm_state(),
        "modules": module_state,
        "input_devices": inputs,
        "steamlink": {"available": bool(steamlink), "path": steamlink or ""},
        "ready": bool(connected) and bool(steamlink),
    }


def bluetooth_scan_devices(seconds: int = 5) -> Dict[str, Any]:
    """Scan for Bluetooth devices."""
    try:
        seconds = max(2, min(12, int(seconds or 5)))
        # Start discovery
        _run(["bluetoothctl", "scan", "on"], t=2)
        # Wait for scan
        import time
        time.sleep(seconds)
        # Stop discovery
        _run(["bluetoothctl", "scan", "off"], t=2)
        # Get scanned devices
        devices = _bt_scanned_devices()
        paired = _bt_paired_devices()
        all_devices = bluetooth_devices()
        return {
            "ok": True,
            "devices": devices,
            "paired": paired,
            "all": all_devices,
            "controller": bluetooth_controller_status(all_devices),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def bluetooth_pair(mac: str) -> Dict[str, Any]:
    """Pair with a Bluetooth device."""
    try:
        r = _run(["bluetoothctl", "pair", mac], t=10)
        output = (r.stdout + r.stderr).strip()[:300]
        return {"ok": r.returncode == 0, "output": output, "result": output}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def bluetooth_trust(mac: str) -> Dict[str, Any]:
    """Trust a Bluetooth device."""
    try:
        r = _run(["bluetoothctl", "trust", mac], t=5)
        output = (r.stdout + r.stderr).strip()[:300]
        return {"ok": r.returncode == 0, "output": output, "result": output}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def bluetooth_connect(mac: str) -> Dict[str, Any]:
    """Connect to a Bluetooth device."""
    try:
        r = _run(["bluetoothctl", "connect", mac], t=10)
        output = (r.stdout + r.stderr).strip()[:300]
        return {"ok": r.returncode == 0, "output": output, "result": output}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def bluetooth_disconnect(mac: str) -> Dict[str, Any]:
    """Disconnect from a Bluetooth device."""
    try:
        r = _run(["bluetoothctl", "disconnect", mac], t=5)
        output = (r.stdout + r.stderr).strip()[:300]
        return {"ok": r.returncode == 0, "output": output, "result": output}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def bluetooth_remove(mac: str) -> Dict[str, Any]:
    """Remove a Bluetooth device."""
    try:
        r = _run(["bluetoothctl", "remove", mac], t=5)
        output = (r.stdout + r.stderr).strip()[:300]
        return {"ok": r.returncode == 0, "output": output, "result": output}
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

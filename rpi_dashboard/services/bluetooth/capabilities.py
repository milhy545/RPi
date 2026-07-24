"""Capability mapping for Bluetooth UUIDs and PC interoperability."""

from __future__ import annotations

from typing import Any


BASE_UUID_SUFFIX = "-0000-1000-8000-00805f9b34fb"


PROFILE_CATALOG: dict[str, dict[str, str]] = {
    f"00001101{BASE_UUID_SUFFIX}": {
        "id": "spp",
        "label": "Serial Port",
        "category": "serial",
        "direction": "bidirectional",
    },
    f"00001105{BASE_UUID_SUFFIX}": {
        "id": "opp",
        "label": "Object Push",
        "category": "file_transfer",
        "direction": "bidirectional",
    },
    f"00001108{BASE_UUID_SUFFIX}": {
        "id": "hsp-headset",
        "label": "Headset",
        "category": "headset",
        "direction": "remote_headset",
    },
    f"0000110a{BASE_UUID_SUFFIX}": {
        "id": "a2dp-source",
        "label": "Audio Source",
        "category": "audio",
        "direction": "receive",
    },
    f"0000110b{BASE_UUID_SUFFIX}": {
        "id": "a2dp-sink",
        "label": "Audio Sink",
        "category": "audio",
        "direction": "send",
    },
    f"0000110c{BASE_UUID_SUFFIX}": {
        "id": "avrcp-target",
        "label": "Media Control Target",
        "category": "media",
        "direction": "control_remote",
    },
    f"0000110e{BASE_UUID_SUFFIX}": {
        "id": "avrcp-controller",
        "label": "Media Control Controller",
        "category": "media",
        "direction": "controlled_by_remote",
    },
    f"00001112{BASE_UUID_SUFFIX}": {
        "id": "hsp-audio-gateway",
        "label": "Headset Audio Gateway",
        "category": "headset",
        "direction": "remote_gateway",
    },
    f"00001115{BASE_UUID_SUFFIX}": {
        "id": "panu",
        "label": "PAN User",
        "category": "network",
        "direction": "client",
    },
    f"00001116{BASE_UUID_SUFFIX}": {
        "id": "nap",
        "label": "Network Access Point",
        "category": "network",
        "direction": "server",
    },
    f"00001117{BASE_UUID_SUFFIX}": {
        "id": "gn",
        "label": "Group Network",
        "category": "network",
        "direction": "server",
    },
    f"0000111e{BASE_UUID_SUFFIX}": {
        "id": "hfp-handsfree",
        "label": "Hands-Free",
        "category": "headset",
        "direction": "remote_handsfree",
    },
    f"0000111f{BASE_UUID_SUFFIX}": {
        "id": "hfp-audio-gateway",
        "label": "Hands-Free Audio Gateway",
        "category": "headset",
        "direction": "remote_gateway",
    },
    f"00001124{BASE_UUID_SUFFIX}": {
        "id": "hid",
        "label": "Human Interface Device",
        "category": "control",
        "direction": "remote_input",
    },
    f"0000180f{BASE_UUID_SUFFIX}": {
        "id": "battery",
        "label": "Battery Service",
        "category": "telemetry",
        "direction": "read",
    },
    f"00001812{BASE_UUID_SUFFIX}": {
        "id": "hogp",
        "label": "HID over GATT",
        "category": "control",
        "direction": "remote_input",
    },
}


def normalize_uuid(value: str) -> str:
    """Normalize a full Bluetooth UUID for deterministic matching."""
    return value.strip().lower()


def capability_summary(uuids: tuple[str, ...] | list[str]) -> dict[str, Any]:
    """Describe only profiles explicitly advertised by a remote device."""
    normalized = [normalize_uuid(value) for value in uuids if value]
    profiles = [dict(PROFILE_CATALOG[value], uuid=value) for value in normalized if value in PROFILE_CATALOG]
    known = {profile["uuid"] for profile in profiles}
    ids = {profile["id"] for profile in profiles}
    return {
        "profiles": profiles,
        "unknown_uuids": [value for value in normalized if value not in known],
        "audio": {
            "send": "a2dp-sink" in ids,
            "receive": "a2dp-source" in ids,
            "headset": bool(ids & {"hsp-headset", "hsp-audio-gateway", "hfp-handsfree", "hfp-audio-gateway"}),
        },
        "media": {
            "control_remote": "avrcp-target" in ids,
            "controlled_by_remote": "avrcp-controller" in ids,
        },
        "control": {"hid": "hid" in ids, "hogp": "hogp" in ids},
        "file_transfer": {"object_push": "opp" in ids},
        "network": {"panu": "panu" in ids, "nap": "nap" in ids, "gn": "gn" in ids},
        "serial": {"spp": "spp" in ids},
        "telemetry": {"battery": "battery" in ids},
    }


from pathlib import Path


def detect_adapter_bus_type(index: int | None, bluez_path: str = "") -> str:
    """Detect whether an adapter is USB or integrated UART via sysfs or path conventions."""
    if index is not None:
        sysfs_link = Path(f"/sys/class/bluetooth/hci{index}")
        if sysfs_link.exists():
            try:
                target = str(sysfs_link.resolve())
                if ".usb" in target.lower() or "/usb" in target.lower():
                    return "usb"
                if any(token in target.lower() for token in ("serial", "uart", "platform")):
                    return "uart"
            except Exception:
                pass
    path_lower = (bluez_path or "").lower()
    if "hci1" in path_lower or "usb" in path_lower:
        return "usb"
    if "hci0" in path_lower:
        return "uart"
    return "unknown"


def recommend_adapter_topology(adapters: list[dict[str, Any]]) -> dict[str, Any]:
    """Recommend optimal adapter assignments for audio vs IO streams."""
    if not adapters:
        return {
            "ok": False,
            "error": "No Bluetooth adapters detected",
            "recommended_audio_adapter": None,
            "recommended_io_adapter": None,
            "adapters": [],
            "warning": "No active Bluetooth hardware available",
        }

    detected = []
    for adapter in adapters:
        idx = adapter.get("index")
        bpath = adapter.get("bluez_path", "")
        bus_type = adapter.get("hardware", {}).get("bus_type") or detect_adapter_bus_type(idx, bpath)
        detected.append({
            "id": adapter.get("id"),
            "name": adapter.get("name") or adapter.get("alias") or (f"hci{idx}" if idx is not None else adapter.get("id")),
            "index": idx,
            "bus_type": bus_type,
            "bus_label": "USB Dongle" if bus_type == "usb" else ("Integrated UART" if bus_type == "uart" else "Standard Adapter"),
        })

    usb_adapter = next((a for a in detected if a["bus_type"] == "usb"), None)
    uart_adapter = next((a for a in detected if a["bus_type"] == "uart"), None)

    if len(detected) >= 2 and usb_adapter and uart_adapter:
        recommended_audio = usb_adapter["id"]
        recommended_io = uart_adapter["id"]
        warning = None
    elif usb_adapter:
        recommended_audio = usb_adapter["id"]
        recommended_io = usb_adapter["id"]
        warning = "Single USB adapter detected; used for both Audio and IO."
    else:
        first_id = detected[0]["id"]
        recommended_audio = first_id
        recommended_io = first_id
        warning = "Only one (integrated UART) adapter detected. Simultaneous multi-speaker streaming may experience stuttering on RPi 3."

    for item in detected:
        roles = []
        if item["id"] == recommended_audio:
            roles.append("audio")
        if item["id"] == recommended_io:
            roles.append("io")
        item["recommended_roles"] = roles

    return {
        "ok": True,
        "recommended_audio_adapter": recommended_audio,
        "recommended_io_adapter": recommended_io,
        "adapters": detected,
        "warning": warning,
    }


def pc_capability_matrix() -> dict[str, dict[str, dict[str, str]]]:
    """Return conservative OS prerequisites; live negotiation remains authoritative."""
    return {
        "windows": {
            "a2dp_sink": {
                "status": "conditional",
                "prerequisite": "Windows PC must advertise an Audio Sink endpoint",
            },
            "a2dp_source": {
                "status": "conditional",
                "prerequisite": "Windows must select the RPi as an audio playback device",
            },
            "hfp_hsp": {
                "status": "conditional",
                "prerequisite": "Both endpoints must negotiate compatible Hands-Free roles",
            },
            "opp": {
                "status": "conditional",
                "prerequisite": "Windows Bluetooth File Transfer must be open for receive/send",
            },
            "hid_host": {
                "status": "conditional",
                "prerequisite": "Windows must accept a trusted HID service explicitly enabled on the RPi",
            },
        },
        "linux": {
            "a2dp_sink": {
                "status": "conditional",
                "prerequisite": "BlueZ and PipeWire must expose an A2DP Sink role",
            },
            "a2dp_source": {
                "status": "conditional",
                "prerequisite": "BlueZ and PipeWire must expose an A2DP Source role",
            },
            "hfp_hsp": {
                "status": "conditional",
                "prerequisite": "WirePlumber and a telephony backend must expose compatible roles",
            },
            "opp": {
                "status": "conditional",
                "prerequisite": "bluez-obex must run with an Object Push agent",
            },
            "hid_host": {
                "status": "conditional",
                "prerequisite": "The remote BlueZ host must authorize the trusted HID service",
            },
        },
    }


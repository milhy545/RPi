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

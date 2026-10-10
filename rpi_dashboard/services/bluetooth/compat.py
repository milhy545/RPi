"""Compatibility helpers for legacy Bluetooth API shapes."""

from __future__ import annotations

from typing import Any

from .models import BluetoothState
from .models import Device


def legacy_device(device: Device) -> dict[str, Any]:
    """Return a legacy MAC-oriented device record with adapter context."""
    return {
        "mac": device.address,
        "name": device.name or device.alias or device.address,
        "kind": _legacy_kind(device.kind),
        "type": _legacy_type(device.kind),
        "paired": device.paired,
        "connected": device.connected,
        "trusted": device.trusted,
        "adapter_id": device.adapter_id,
        "device_key": device.key,
        "services_resolved": device.services_resolved,
        "rssi": device.rssi,
        "battery_percentage": device.battery_percentage,
    }


def legacy_devices(state: BluetoothState) -> list[dict[str, Any]]:
    """Return legacy records sorted like the old flat Bluetooth list."""
    records = [legacy_device(device) for device in state.devices if device.present]
    return sorted(
        records,
        key=lambda item: (
            not item["connected"],
            not item["paired"],
            item["kind"],
            item["name"].lower(),
            item["adapter_id"],
        ),
    )


def legacy_state(state: BluetoothState) -> dict[str, Any]:
    """Embed the v2 state into the existing `/devices/state` contract."""
    devices = legacy_devices(state)
    paired = [device for device in devices if device["paired"]]
    scanned = [device for device in devices if not device["paired"]]
    controller = state.diagnostics.get("controllers", {})
    if isinstance(controller, dict) and "connected" not in controller:
        connected = [
            device for device in devices
            if device["connected"] and device["kind"] in {"xbox_controller", "gamepad"}
        ]
        controller = dict(controller)
        controller["connected"] = connected
    return {
        "devices": devices,
        "paired": paired,
        "scanned": scanned,
        "controller": controller,
        "v2": state.to_dict(),
    }


def _legacy_kind(kind: str) -> str:
    if kind == "gamepad":
        return "gamepad"
    return kind


def _legacy_type(kind: str) -> str:
    if kind in {"speaker", "audio"}:
        return "audio_output"
    if kind in {"gamepad", "xbox_controller"}:
        return "gamepad"
    if kind in {"keyboard", "mouse", "input"}:
        return "input"
    return "unknown"

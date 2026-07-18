"""Tests for Bluetooth service facade and API handlers."""

from urllib.parse import parse_qs

import pytest

from rpi_dashboard.api import handlers
from rpi_dashboard.services import devices
from rpi_dashboard.services.bluetooth.fake import FakeBluetoothBackend
from rpi_dashboard.services.bluetooth.service import set_backend_for_tests


@pytest.fixture(autouse=True)
def reset_backend():
    """Reset the Bluetooth backend singleton after each test."""
    set_backend_for_tests(None)
    yield
    set_backend_for_tests(None)


def test_bt_state_handler_returns_adapter_aware_contract():
    """The new API exposes the versioned Bluetooth state."""
    set_backend_for_tests(FakeBluetoothBackend.with_soundbar_and_controller())

    result = handlers.handle_bt_state({})

    assert result["ok"] is True
    assert result["schema_version"] == 2
    assert len(result["adapters"]) == 2
    assert all("adapter_id" in device for device in result["devices"])
    assert "soundbar" in result["diagnostics"]


def test_bt_device_action_uses_adapter_and_device_key():
    """Adapter-aware actions update the selected fake device."""
    backend = FakeBluetoothBackend.with_soundbar_and_controller()
    set_backend_for_tests(backend)
    state = handlers.handle_bt_state({})
    controller = next(device for device in state["devices"] if device["kind"] == "gamepad")

    result = handlers.handle_bt_device_action(
        parse_qs(
            "action=disconnect"
            f"&adapter_id={controller['adapter_id']}"
            f"&device_key={controller['key']}"
        )
    )

    assert result["ok"] is True
    assert result["operation"]["type"] == "disconnect"
    updated = handlers.handle_bt_state({})
    disconnected = next(device for device in updated["devices"] if device["key"] == controller["key"])
    assert disconnected["connected"] is False


def test_bt_adapter_power_handler_updates_adapter():
    """Adapter power control flows through the shared backend."""
    backend = FakeBluetoothBackend.one_adapter()
    set_backend_for_tests(backend)
    adapter_id = handlers.handle_bt_state({})["adapters"][0]["id"]

    result = handlers.handle_bt_adapter_power(
        parse_qs(f"adapter_id={adapter_id}&powered=0")
    )

    assert result["ok"] is True
    state = handlers.handle_bt_state({})
    assert state["adapters"][0]["powered"] is False


def test_legacy_mac_action_rejects_ambiguous_device():
    """MAC-only actions do not silently choose the first adapter."""
    set_backend_for_tests(FakeBluetoothBackend.with_overlapping_remote())

    result = handlers.handle_bt_connect(parse_qs("mac=DD:EE:FF:00:00:09"))

    assert result["ok"] is False
    assert result["code"] == "ambiguous_device"


def test_devices_state_embeds_v2_bluetooth_without_breaking_legacy_fields(monkeypatch):
    """`/devices/state` keeps legacy fields and includes v2 state."""
    set_backend_for_tests(FakeBluetoothBackend.with_soundbar_and_controller())
    monkeypatch.setattr(devices, "wifi_status", lambda: {"available": False})

    result = devices.devices_state()

    bluetooth = result["bluetooth"]
    assert result["ok"] is True
    assert bluetooth["devices"]
    assert bluetooth["paired"]
    assert bluetooth["v2"]["schema_version"] == 2
    assert "mac" in bluetooth["devices"][0]
    assert "adapter_id" in bluetooth["devices"][0]


def test_bt_state_enriches_soundbar_with_audio_readiness(monkeypatch):
    """Bluetooth state composes Audio-owned soundbar evidence."""
    set_backend_for_tests(FakeBluetoothBackend.with_soundbar_and_controller())

    from rpi_dashboard.services import audio

    monkeypatch.setattr(
        audio,
        "audio_state",
        lambda: {
            "default_sink": "bluez_output.24_4B_03_92_0B_8C.1",
            "devices": {
                "bt_soundbar": {
                    "present": True,
                    "name": "bluez_output.24_4B_03_92_0B_8C.1",
                }
            },
            "routes": {"alexa_to_bt": {"on": False}},
        },
    )

    result = handlers.handle_bt_state({})
    steps = {
        step["id"]: step
        for step in result["diagnostics"]["soundbar"]["steps"]
    }

    assert steps["pipewire_sink"]["state"] is True
    assert steps["route"]["state"] is True
    assert steps["route"]["reason"] == "Soundbar is default sink"

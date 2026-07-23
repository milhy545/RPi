"""Tests for Bluetooth service facade and API handlers."""

import asyncio
from urllib.parse import parse_qs

import pytest

from rpi_dashboard.api import handlers
from rpi_dashboard.services import devices
from rpi_dashboard.services.bluetooth.bluez import BlueZDbusBackend
from rpi_dashboard.services.bluetooth.fake import FakeBluetoothBackend
from rpi_dashboard.services.bluetooth.service import set_backend_for_tests
from rpi_dashboard.services.bluetooth import service as bluetooth_service


@pytest.fixture(autouse=True)
def reset_backend(monkeypatch, tmp_path):
    """Reset the Bluetooth backend singleton after each test."""
    monkeypatch.setenv("RPI_BLUETOOTH_SETTINGS_PATH", str(tmp_path / "bluetooth.json"))
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


def test_sync_facade_reuses_one_persistent_event_loop():
    async def loop_identity():
        return id(asyncio.get_running_loop())

    assert bluetooth_service._run(loop_identity()) == bluetooth_service._run(loop_identity())


def test_sync_runner_cancels_stalled_operation():
    runner = bluetooth_service._AsyncRunner()

    with pytest.raises(TimeoutError, match="timed out after"):
        runner.run(asyncio.sleep(10), timeout=0.01)


def test_state_read_does_not_trigger_auto_connect(monkeypatch):
    backend = FakeBluetoothBackend.with_soundbar_and_controller()
    set_backend_for_tests(backend)
    monkeypatch.setattr(
        bluetooth_service,
        "_apply_auto_connect",
        lambda *_args, **_kwargs: pytest.fail("state read triggered auto-connect"),
    )

    result = handlers.handle_bt_state({})

    assert result["ok"] is True


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
    assert result["result"] == "disconnect succeeded"
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


def test_adapter_id_disambiguates_legacy_mac_action():
    """An explicit adapter filters overlapping MAC relationships."""
    backend = FakeBluetoothBackend.with_overlapping_remote()
    set_backend_for_tests(backend)
    state = handlers.handle_bt_state({})
    adapter_id = state["adapters"][0]["id"]

    result = handlers.handle_bt_connect(
        parse_qs(f"mac=DD:EE:FF:00:00:09&adapter_id={adapter_id}")
    )

    assert result["ok"] is True
    connected = [
        device for device in handlers.handle_bt_state({})["devices"]
        if device["connected"]
    ]
    assert [device["adapter_id"] for device in connected] == [adapter_id]


def test_bt_discoverability_and_settings_are_real_backend_operations(tmp_path, monkeypatch):
    backend = FakeBluetoothBackend.one_adapter()
    set_backend_for_tests(backend)
    monkeypatch.setenv("RPI_BLUETOOTH_SETTINGS_PATH", str(tmp_path / "bluetooth.json"))
    adapter_id = handlers.handle_bt_state({})["adapters"][0]["id"]

    setting = handlers.handle_bt_settings(parse_qs("auto_connect=0&discoverable_timeout=300"))
    discoverable = handlers.handle_bt_discoverable(
        parse_qs(f"adapter_id={adapter_id}&discoverable=1&timeout=300")
    )
    state = handlers.handle_bt_state({})

    assert setting["ok"] is True
    assert setting["settings"]["discoverable_timeout"] == 300
    assert discoverable["ok"] is True
    assert state["adapters"][0]["discoverable"] is True
    assert state["settings"]["auto_connect"] is False


def test_enabling_auto_connect_reconnects_trusted_paired_devices():
    backend = FakeBluetoothBackend.with_soundbar_and_controller()
    set_backend_for_tests(backend)
    initial = handlers.handle_bt_state({})
    device = initial["devices"][0]
    disconnected = handlers.handle_bt_device_action(
        parse_qs(
            "action=disconnect"
            f"&adapter_id={device['adapter_id']}"
            f"&device_key={device['key']}"
        )
    )
    assert disconnected["ok"] is True

    enabled = handlers.handle_bt_settings(parse_qs("auto_connect=1"))
    state = handlers.handle_bt_state({})

    assert enabled["ok"] is True
    assert next(item for item in state["devices"] if item["key"] == device["key"])[
        "connected"
    ] is True


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


def test_bluez_backend_delegates_operations_when_state_is_from_fallback(monkeypatch):
    """Fallback state must not be used as invalid D-Bus object paths."""
    fallback = FakeBluetoothBackend.with_soundbar_and_controller()
    backend = BlueZDbusBackend(fallback=fallback)

    async def broken_bluez_state():
        raise RuntimeError("dbus unavailable")

    monkeypatch.setattr(backend, "_state_from_bluez", broken_bluez_state)
    set_backend_for_tests(backend)

    state = handlers.handle_bt_state({})
    adapter_id = state["adapters"][0]["id"]

    result = handlers.handle_bt_discovery(
        parse_qs(f"action=start&adapter_id={adapter_id}")
    )

    assert result["ok"] is True
    assert result["operation"]["type"] == "start_discovery"
    assert result["operation"]["adapter_id"] == adapter_id

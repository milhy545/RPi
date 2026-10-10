"""Tests for the Bluetooth control center domain foundation."""

import asyncio

import pytest

from rpi_dashboard.services.bluetooth.fake import FakeBluetoothBackend
from rpi_dashboard.services.bluetooth.fake import fake_adapter
from rpi_dashboard.services.bluetooth.fake import fake_device
from rpi_dashboard.services.bluetooth.models import BluetoothError
from rpi_dashboard.services.bluetooth.models import SCHEMA_VERSION
from rpi_dashboard.services.bluetooth.models import adapter_id_from_address
from rpi_dashboard.services.bluetooth.models import classify_device
from rpi_dashboard.services.bluetooth.models import hide_non_owner_duplicates
from rpi_dashboard.services.bluetooth.models import make_device_key


@pytest.mark.asyncio
async def test_empty_fake_backend_serializes_schema():
    """Zero-adapter state stays deterministic and hardware-free."""
    backend = FakeBluetoothBackend.empty()

    state = (await backend.state()).to_dict()

    assert state["ok"] is True
    assert state["schema_version"] == SCHEMA_VERSION
    assert state["backend"]["name"] == "fake"
    assert state["adapters"] == []
    assert state["devices"] == []
    assert state["operations"] == []
    assert state["diagnostics"]["bluez"] == {
        "available": True,
        "source": "fake",
    }


@pytest.mark.asyncio
async def test_two_adapters_have_stable_ids_not_indexes():
    """Adapter identity follows the public address, not hci numbering."""
    first = fake_adapter(address="AA:BB:CC:00:00:01", index=0)
    renumbered = fake_adapter(address="AA:BB:CC:00:00:01", index=3)

    assert first.id == renumbered.id
    assert first.bluez_path != renumbered.bluez_path

    backend = FakeBluetoothBackend(adapters=[first])
    backend.remove_adapter(first.id)
    backend.add_adapter(renumbered)

    adapters = (await backend.state()).to_dict()["adapters"]
    present = [adapter for adapter in adapters if adapter["present"]]
    assert present[0]["id"] == adapter_id_from_address("AA:BB:CC:00:00:01")
    assert present[0]["index"] == 3


@pytest.mark.asyncio
async def test_overlapping_remote_address_is_scoped_to_adapter():
    """The same remote MAC on two adapters produces two device records."""
    backend = FakeBluetoothBackend.with_overlapping_remote()

    devices = (await backend.state()).to_dict()["devices"]

    assert len(devices) == 2
    assert {device["address"] for device in devices} == {"DD:EE:FF:00:00:09"}
    assert len({device["adapter_id"] for device in devices}) == 2
    assert len({device["key"] for device in devices}) == 2


def test_paired_owner_hides_unpaired_shadow_on_other_adapter():
    """A discovered duplicate is hidden once one adapter owns the bond."""
    adapters = list(FakeBluetoothBackend.two_adapters()._adapters.values())
    owner = fake_device(
        adapters[0].id,
        "DD:EE:FF:00:00:09",
        paired=True,
        trusted=True,
    )
    shadow = fake_device(adapters[1].id, "DD:EE:FF:00:00:09")

    visible = hide_non_owner_duplicates([owner, shadow])

    assert visible == [owner]


def test_two_real_bonds_are_not_silently_merged():
    """Ambiguous pre-existing bonds remain visible for explicit cleanup."""
    adapters = list(FakeBluetoothBackend.two_adapters()._adapters.values())
    devices = [
        fake_device(adapters[0].id, "DD:EE:FF:00:00:09", paired=True),
        fake_device(adapters[1].id, "DD:EE:FF:00:00:09", paired=True),
    ]

    assert hide_non_owner_duplicates(devices) == devices


@pytest.mark.asyncio
async def test_hotplug_marks_adapter_and_devices_absent():
    """Adapter removal keeps history but makes presence explicit."""
    backend = FakeBluetoothBackend.one_adapter()
    adapter_id = (await backend.state()).adapters[0].id
    backend.add_device(fake_device(adapter_id, "DD:EE:FF:00:00:09"))

    backend.remove_adapter(adapter_id)
    state = (await backend.state()).to_dict()

    assert state["adapters"][0]["present"] is False
    assert state["adapters"][0]["powered"] is False
    assert state["devices"][0]["present"] is False
    assert state["events"][-1]["type"] == "adapter_removed"


@pytest.mark.asyncio
async def test_adapter_and_device_operations_update_state():
    """Fake operations exercise the state contract without subprocesses."""
    backend = FakeBluetoothBackend.one_adapter()
    adapter = (await backend.state()).adapters[0]
    device = fake_device(adapter.id, "DD:EE:FF:00:00:09")
    backend.add_device(device)

    await backend.start_discovery(adapter.id)
    await backend.pair(adapter.id, device.key)
    await backend.trust(adapter.id, device.key)
    await backend.connect(adapter.id, device.key)

    state = await backend.state()
    serialized = state.to_dict()
    updated = serialized["devices"][0]
    assert serialized["adapters"][0]["discovering"] is True
    assert updated["paired"] is True
    assert updated["trusted"] is True
    assert updated["connected"] is True
    assert serialized["operations"][-1]["state"] == "succeeded"


@pytest.mark.asyncio
async def test_missing_adapter_returns_structured_error():
    """Backend failures use stable error codes and target context."""
    backend = FakeBluetoothBackend.empty()

    operation = await backend.start_discovery("missing-adapter")

    assert operation.state == "failed"
    assert operation.error is not None
    assert operation.error.code == "adapter_missing"
    assert operation.error.retryable is True
    assert operation.error.adapter_id == "missing-adapter"


@pytest.mark.asyncio
async def test_scripted_operation_error_is_reported():
    """Fake backend can force deterministic operation failures."""
    backend = FakeBluetoothBackend.one_adapter()
    adapter = (await backend.state()).adapters[0]
    device = fake_device(adapter.id, "DD:EE:FF:00:00:09")
    backend.add_device(device)
    backend.script_error(
        "connect",
        BluetoothError(
            "connection_failed",
            "Connection rejected by fake scenario",
            retryable=True,
            adapter_id=adapter.id,
            device_key=device.key,
        ),
    )

    operation = await backend.connect(adapter.id, device.key)

    assert operation.state == "failed"
    assert operation.error is not None
    assert operation.error.code == "connection_failed"
    assert (await backend.state()).to_dict()["events"][-1]["type"] == "operation_failed"


@pytest.mark.asyncio
async def test_pending_pair_can_be_cancelled_without_late_success():
    backend = FakeBluetoothBackend.one_adapter()
    adapter = (await backend.state()).adapters[0]
    device = fake_device(adapter.id, "DD:EE:FF:00:00:09")
    backend.add_device(device)
    backend.script_delay("pair", 0.05)

    task = asyncio.create_task(backend.pair(adapter.id, device.key))
    await asyncio.sleep(0)
    pending = next(item for item in (await backend.state()).operations if item.state == "pending")
    cancelled = await backend.cancel(pending.id)
    result = await task

    assert cancelled.state == "cancelled"
    assert result.state == "cancelled"
    assert backend._devices[device.key].paired is False


@pytest.mark.asyncio
async def test_soundbar_and_controller_readiness_are_evidence_backed():
    """Readiness diagnostics keep Bluetooth and Audio evidence separate."""
    backend = FakeBluetoothBackend.with_soundbar_and_controller()

    diagnostics = (await backend.state()).to_dict()["diagnostics"]

    soundbar = diagnostics["soundbar"]
    assert soundbar["ready"] is True
    assert soundbar["steps"][0]["id"] == "adapter"
    assert soundbar["steps"][5]["id"] == "services"
    assert soundbar["steps"][6]["state"] is None
    assert "Audio service" in soundbar["steps"][6]["reason"]

    controllers = diagnostics["controllers"]
    assert controllers["ready"] is False
    assert controllers["controllers"]
    assert "Linux input evidence unavailable in fake backend" in controllers["blockers"]


@pytest.mark.asyncio
async def test_device_keys_are_adapter_scoped():
    """Device keys include adapter identity and preserve nullable telemetry."""
    adapter_id = adapter_id_from_address("AA:BB:CC:00:00:01")
    device = fake_device(adapter_id, "DD:EE:FF:00:00:09")

    serialized = device.to_dict()

    assert device.key == make_device_key(adapter_id, "DD:EE:FF:00:00:09")
    assert serialized["adapter_id"] == adapter_id
    assert "rssi" not in serialized
    assert "battery_percentage" not in serialized


def test_device_classification_tolerates_null_bluez_properties():
    assert classify_device(None, None, (None,)) == ("unknown", (), "unknown")

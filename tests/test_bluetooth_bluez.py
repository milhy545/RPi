"""Tests for BlueZ D-Bus state mapping and bounded operations."""

import asyncio
from types import SimpleNamespace

import pytest

dbus_fast = pytest.importorskip("dbus_fast")
Variant = dbus_fast.Variant
MessageType = dbus_fast.MessageType

from rpi_dashboard.services.bluetooth.bluez import ADAPTER1
from rpi_dashboard.services.bluetooth.bluez import BATTERY1
from rpi_dashboard.services.bluetooth.bluez import DEVICE1
from rpi_dashboard.services.bluetooth.bluez import MEDIA_PLAYER1
from rpi_dashboard.services.bluetooth.bluez import MEDIA_TRANSPORT1
from rpi_dashboard.services.bluetooth.bluez import BlueZDbusBackend
from rpi_dashboard.services.bluetooth.bluez import _adapters_from_managed
from rpi_dashboard.services.bluetooth.bluez import _devices_from_managed
from rpi_dashboard.services.bluetooth.bluez import _index_from_path
from rpi_dashboard.services.bluetooth.bluez import _preferred_connect_profile
from rpi_dashboard.services.bluetooth.bluez import _media_from_managed
from rpi_dashboard.services.bluetooth.fake import fake_device
from rpi_dashboard.services.bluetooth.fake import fake_adapter
from rpi_dashboard.services.bluetooth.models import BluetoothState
from rpi_dashboard.services.bluetooth.models import BackendHealth


def test_bluez_managed_objects_map_two_adapters_and_devices():
    """ObjectManager data becomes adapter-scoped domain records."""
    managed = {
        "/org/bluez/hci0": {
            ADAPTER1: {
                "Address": Variant("s", "AA:BB:CC:00:00:01"),
                "AddressType": Variant("s", "public"),
                "Name": Variant("s", "rpi"),
                "Alias": Variant("s", "Onboard BT"),
                "Powered": Variant("b", True),
                "Discoverable": Variant("b", False),
                "Pairable": Variant("b", True),
                "Discovering": Variant("b", False),
            }
        },
        "/org/bluez/hci1": {
            ADAPTER1: {
                "Address": Variant("s", "AA:BB:CC:00:00:02"),
                "AddressType": Variant("s", "public"),
                "Name": Variant("s", "usb"),
                "Alias": Variant("s", "USB BT"),
                "Powered": Variant("b", True),
                "Discoverable": Variant("b", False),
                "Pairable": Variant("b", True),
                "Discovering": Variant("b", True),
            }
        },
        "/org/bluez/hci0/dev_DD_EE_FF_00_00_09": {
            DEVICE1: {
                "Address": Variant("s", "DD:EE:FF:00:00:09"),
                "Name": Variant("s", "[Samsung] Soundbar J-Series"),
                "Alias": Variant("s", "[Samsung] Soundbar J-Series"),
                "Icon": Variant("s", "audio-card"),
                "UUIDs": Variant("as", ["0000110b-0000-1000-8000-00805f9b34fb"]),
                "Paired": Variant("b", True),
                "Bonded": Variant("b", True),
                "Trusted": Variant("b", True),
                "Connected": Variant("b", True),
                "ServicesResolved": Variant("b", True),
                "RSSI": Variant("n", -44),
            },
            BATTERY1: {"Percentage": Variant("y", 87)},
        },
        "/org/bluez/hci1/dev_DD_EE_FF_00_00_09": {
            DEVICE1: {
                "Address": Variant("s", "DD:EE:FF:00:00:09"),
                "Name": Variant("s", "Xbox Wireless Controller"),
                "Alias": Variant("s", "Xbox Wireless Controller"),
                "Icon": Variant("s", "input-gaming"),
                "UUIDs": Variant("as", ["00001124-0000-1000-8000-00805f9b34fb"]),
                "Paired": Variant("b", True),
                "Trusted": Variant("b", False),
                "Connected": Variant("b", False),
                "ServicesResolved": Variant("b", False),
            }
        },
    }

    adapters = _adapters_from_managed(managed)
    devices = _devices_from_managed(managed, adapters)

    assert [adapter.index for adapter in adapters] == [0, 1]
    assert adapters[0].id != adapters[1].id
    assert len(devices) == 2
    assert len({device.key for device in devices}) == 2
    assert {device.address for device in devices} == {"DD:EE:FF:00:00:09"}
    assert {device.adapter_id for device in devices} == {adapter.id for adapter in adapters}
    soundbar = next(device for device in devices if device.kind == "speaker")
    assert soundbar.rssi == -44
    assert soundbar.battery_percentage == 87
    assert soundbar.bonded is True


def test_bluez_path_index_rejects_non_hci_paths():
    assert _index_from_path("/org/bluez/hci12/dev_AA") == 12
    assert _index_from_path("bluetoothctl://AA:BB") is None


def test_speaker_prefers_explicit_a2dp_sink_profile():
    speaker = fake_device(
        "adapter-a",
        "24:4B:03:92:0B:8C",
        name="[Samsung] Soundbar J-Series",
        icon="audio-card",
        uuids=("0000110b-0000-1000-8000-00805f9b34fb",),
    )

    assert _preferred_connect_profile(speaker) == "0000110b-0000-1000-8000-00805f9b34fb"


def test_phone_prefers_explicit_a2dp_source_profile():
    phone = fake_device(
        "adapter-b",
        "1C:D1:07:52:E1:1A",
        name="realme 8 5G",
        icon="phone",
        uuids=("0000110a-0000-1000-8000-00805f9b34fb",),
    )

    assert _preferred_connect_profile(phone) == "0000110a-0000-1000-8000-00805f9b34fb"


def test_bluez_media_objects_are_scoped_to_owning_device():
    adapter = fake_adapter(address="AA:BB:CC:00:00:01", index=0)
    device = fake_device(adapter.id, "DD:EE:FF:00:00:09")
    managed = {
        f"{device.bluez_path}/player0": {
            MEDIA_PLAYER1: {
                "Name": Variant("s", "Phone Player"),
                "Status": Variant("s", "playing"),
                "Track": Variant("a{sv}", {"Title": Variant("s", "Song")}),
            }
        },
        f"{device.bluez_path}/sep1/fd0": {
            MEDIA_TRANSPORT1: {
                "UUID": Variant("s", "0000110a-0000-1000-8000-00805f9b34fb"),
                "State": Variant("s", "active"),
                "Codec": Variant("y", 0),
                "Volume": Variant("q", 96),
                "Delay": Variant("q", 120),
            }
        },
    }

    media = _media_from_managed(managed, [device])

    assert media["players"][0]["device_key"] == device.key
    assert media["players"][0]["track"]["Title"] == "Song"
    assert media["transports"][0]["volume"] == 96
    assert media["transports"][0]["delay"] == 120


def test_bluez_property_signal_is_bounded_and_adapter_scoped():
    adapter = fake_adapter(address="AA:BB:CC:00:00:01", index=0)
    device = fake_device(adapter.id, "DD:EE:FF:00:00:09")
    backend = BlueZDbusBackend(history_limit=2)
    backend._last_state = BluetoothState(
        backend=BackendHealth(name="fake"),
        adapters=(adapter,),
        devices=(device,),
    )

    for value in (-60, -55, -50):
        backend._handle_bluez_signal(
            SimpleNamespace(
                message_type=MessageType.SIGNAL,
                interface="org.freedesktop.DBus.Properties",
                member="PropertiesChanged",
                path=device.bluez_path,
                body=[DEVICE1, {"RSSI": Variant("n", value)}, []],
            )
        )

    assert len(backend._events) == 2
    assert backend._event_queue.qsize() == 2
    assert backend._events[-1].type == "device_changed"
    assert backend._events[-1].adapter_id == adapter.id
    assert backend._events[-1].device_key == device.key


@pytest.mark.asyncio
async def test_signal_subscriptions_are_restored_for_new_bus():
    class Bus:
        connected = True

        def __init__(self):
            self.handlers = []
            self.calls = []

        def add_message_handler(self, handler):
            self.handlers.append(handler)

        async def call(self, message):
            self.calls.append(message)
            return SimpleNamespace(message_type=object())

    backend = BlueZDbusBackend()
    first = Bus()
    second = Bus()

    await backend._ensure_signal_subscriptions(first)
    await backend._ensure_signal_subscriptions(first)
    await backend._ensure_signal_subscriptions(second)

    assert len(first.handlers) == 1
    assert len(first.calls) == 2
    assert len(second.handlers) == 1
    assert len(second.calls) == 2


@pytest.mark.asyncio
async def test_no_argument_dbus_method_uses_empty_signature():
    class Bus:
        connected = True

        async def call(self, message):
            self.message = message
            return SimpleNamespace(message_type=object())

    bus = Bus()
    backend = BlueZDbusBackend(operation_timeout=0.2)

    async def connect():
        return bus

    backend._connect = connect
    operation = await backend._call_method(
        "start_discovery",
        "/org/bluez/hci0",
        ADAPTER1,
        "StartDiscovery",
    )

    assert operation.state == "succeeded"
    assert bus.message.signature == ""


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("operation_type", "member", "error_name", "detail"),
    [
        ("start_discovery", "StartDiscovery", "org.bluez.Error.InProgress", "Operation already in progress"),
        ("stop_discovery", "StopDiscovery", "org.bluez.Error.NotReady", "Resource Not Ready"),
    ],
)
async def test_discovery_methods_are_idempotent(operation_type, member, error_name, detail):
    class Bus:
        connected = True

        async def call(self, message):
            return SimpleNamespace(
                message_type=MessageType.ERROR,
                error_name=error_name,
                body=[detail],
            )

    backend = BlueZDbusBackend(operation_timeout=0.2)

    async def connect():
        return Bus()

    backend._connect = connect
    operation = await backend._call_method(
        operation_type,
        "/org/bluez/hci0",
        ADAPTER1,
        member,
    )

    assert operation.state == "succeeded"
    assert operation.result["already_in_state"] is True


@pytest.mark.asyncio
async def test_dbus_method_timeout_returns_structured_failure():
    class Bus:
        connected = True

        async def call(self, message):
            await asyncio.sleep(1)

    backend = BlueZDbusBackend(operation_timeout=0.01)

    async def connect():
        return Bus()

    backend._connect = connect
    operation = await backend._call_method(
        "connect",
        "/org/bluez/hci0/dev_AA",
        DEVICE1,
        "Connect",
    )

    assert operation.state == "failed"
    assert operation.error is not None
    assert operation.error.code == "backend_unavailable"
    assert backend._operations[-1] == operation
    assert backend._events[-1].type == "operation_failed"


@pytest.mark.asyncio
async def test_device_block_sets_adapter_scoped_bluez_property():
    class Bus:
        connected = True

        async def call(self, message):
            self.message = message
            return SimpleNamespace(message_type=object())

    adapter = fake_adapter(address="AA:BB:CC:00:00:01", index=0)
    device = fake_device(adapter.id, "DD:EE:FF:00:00:09")
    backend = BlueZDbusBackend(operation_timeout=0.2)

    async def state():
        return BluetoothState(
            backend=BackendHealth(name="bluez-dbus"),
            adapters=(adapter,),
            devices=(device,),
        )

    bus = Bus()

    async def connect():
        return bus

    backend.state = state
    backend._connect = connect
    operation = await backend.block(adapter.id, device.key)

    assert operation.state == "succeeded"
    assert bus.message.path == device.bluez_path
    assert bus.message.member == "Set"
    assert bus.message.signature == "ssv"
    assert bus.message.body[0:2] == [DEVICE1, "Blocked"]
    assert bus.message.body[2].value is True


@pytest.mark.asyncio
async def test_device_profile_operation_requires_advertised_uuid():
    class Bus:
        connected = True

        async def call(self, message):
            self.message = message
            return SimpleNamespace(message_type=object())

    adapter = fake_adapter(address="AA:BB:CC:00:00:01", index=0)
    profile_uuid = "0000110b-0000-1000-8000-00805f9b34fb"
    device = fake_device(adapter.id, "DD:EE:FF:00:00:09", uuids=(profile_uuid,))
    backend = BlueZDbusBackend(operation_timeout=0.2)

    async def state():
        return BluetoothState(
            backend=BackendHealth(name="bluez-dbus"),
            adapters=(adapter,),
            devices=(device,),
        )

    bus = Bus()

    async def connect():
        return bus

    backend.state = state
    backend._connect = connect

    operation = await backend.connect_profile(adapter.id, device.key, profile_uuid.upper())
    unavailable = await backend.connect_profile(
        adapter.id,
        device.key,
        "0000111e-0000-1000-8000-00805f9b34fb",
    )

    assert operation.state == "succeeded"
    assert bus.message.member == "ConnectProfile"
    assert bus.message.signature == "s"
    assert bus.message.body == [profile_uuid]
    assert unavailable.state == "failed"
    assert unavailable.error is not None
    assert unavailable.error.code == "profile_unavailable"


@pytest.mark.asyncio
async def test_bluez_serializes_conflicting_operations_per_target():
    entered = asyncio.Event()
    release = asyncio.Event()

    class Bus:
        connected = True

        async def call(self, message):
            entered.set()
            await release.wait()
            return SimpleNamespace(message_type=object())

    backend = BlueZDbusBackend(operation_timeout=0.5)

    async def connect():
        return Bus()

    backend._connect = connect
    first_task = asyncio.create_task(
        backend._call_method(
            "connect",
            "/org/bluez/hci0/dev_AA",
            DEVICE1,
            "Connect",
            adapter_id="adapter-a",
            device_key="adapter-a/AA",
        )
    )
    await entered.wait()
    conflict = await backend._call_method(
        "disconnect",
        "/org/bluez/hci0/dev_AA",
        DEVICE1,
        "Disconnect",
        adapter_id="adapter-a",
        device_key="adapter-a/AA",
    )
    release.set()
    first = await first_task

    assert first.state == "succeeded"
    assert conflict.state == "failed"
    assert conflict.error is not None
    assert conflict.error.code == "operation_busy"

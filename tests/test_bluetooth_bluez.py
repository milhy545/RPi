"""Tests for BlueZ D-Bus state mapping."""

import pytest

dbus_fast = pytest.importorskip("dbus_fast")
Variant = dbus_fast.Variant

from rpi_dashboard.services.bluetooth.bluez import ADAPTER1
from rpi_dashboard.services.bluetooth.bluez import BATTERY1
from rpi_dashboard.services.bluetooth.bluez import DEVICE1
from rpi_dashboard.services.bluetooth.bluez import _adapters_from_managed
from rpi_dashboard.services.bluetooth.bluez import _devices_from_managed


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

"""Tests for Bluetooth Setup Wizard backend API endpoints and service functions."""

import pytest
from unittest.mock import patch, MagicMock

from rpi_dashboard.services.bluetooth import (
    reset_all_devices,
    get_adapter_recommendations,
    set_phone_role,
    start_discovery,
)
from rpi_dashboard.services.bluetooth.capabilities import (
    detect_adapter_bus_type,
    recommend_adapter_topology,
)
from rpi_dashboard.api.handlers import (
    handle_bt_reset,
    handle_bt_capabilities,
    handle_bt_phone_role,
)


def test_detect_adapter_bus_type_conventions():
    """USB vs UART bus type detection should handle path and index conventions correctly."""
    assert detect_adapter_bus_type(1, "/org/bluez/hci1") == "usb"
    assert detect_adapter_bus_type(0, "/org/bluez/hci0") == "uart"
    assert detect_adapter_bus_type(None, "/org/bluez/hci_usb1") == "usb"


def test_recommend_adapter_topology_dual_adapters():
    """Dual adapter setup (USB + UART) should assign USB for Audio and UART for IO."""
    adapters = [
        {"id": "adapter-001122334455", "index": 0, "bluez_path": "/org/bluez/hci0", "hardware": {"bus_type": "uart"}},
        {"id": "adapter-66778899aabb", "index": 1, "bluez_path": "/org/bluez/hci1", "hardware": {"bus_type": "usb"}},
    ]
    res = recommend_adapter_topology(adapters)

    assert res["ok"] is True
    assert res["recommended_audio_adapter"] == "adapter-66778899aabb"
    assert res["recommended_io_adapter"] == "adapter-001122334455"
    assert res["warning"] is None
    assert len(res["adapters"]) == 2


def test_recommend_adapter_topology_single_uart_adapter():
    """Single UART adapter should return warning regarding multi-speaker streaming bottleneck."""
    adapters = [
        {"id": "adapter-001122334455", "index": 0, "bluez_path": "/org/bluez/hci0", "hardware": {"bus_type": "uart"}},
    ]
    res = recommend_adapter_topology(adapters)

    assert res["ok"] is True
    assert res["recommended_audio_adapter"] == "adapter-001122334455"
    assert res["recommended_io_adapter"] == "adapter-001122334455"
    assert "integrated UART" in res["warning"] or "single" in res["warning"].lower()


def test_reset_all_devices_unpairs_paired_and_connected():
    """reset_all_devices should call remove on all paired/connected devices."""
    mock_dev1 = MagicMock(paired=True, connected=False, adapter_id="adapter-0", key="adapter-0/AA:BB:CC:DD:EE:FF")
    mock_dev2 = MagicMock(paired=False, connected=True, adapter_id="adapter-1", key="adapter-1/11:22:33:44:55:66")
    mock_dev3 = MagicMock(paired=False, connected=False, adapter_id="adapter-0", key="adapter-0/00:00:00:00:00:00")
    
    mock_state = MagicMock(devices=[mock_dev1, mock_dev2, mock_dev3])
    mock_op = MagicMock(state="succeeded")
    
    from unittest.mock import AsyncMock
    mock_backend = MagicMock()
    mock_backend.state = AsyncMock(return_value=mock_state)
    mock_backend.remove = AsyncMock(return_value=mock_op)

    with patch("rpi_dashboard.services.bluetooth.service.get_backend", return_value=mock_backend):
        res = reset_all_devices()

    assert res["ok"] is True
    assert res["unpaired_count"] == 2
    assert "adapter-0/AA:BB:CC:DD:EE:FF" in res["unpaired_devices"]
    assert "adapter-1/11:22:33:44:55:66" in res["unpaired_devices"]


def test_handle_bt_reset_endpoint():
    """handle_bt_reset API handler should return reset result."""
    with patch("rpi_dashboard.services.bluetooth.service.reset_all_devices") as mock_reset:
        mock_reset.return_value = {"ok": True, "unpaired_count": 1}
        res = handle_bt_reset({})
        assert res["ok"] is True
        assert res["unpaired_count"] == 1


def test_handle_bt_capabilities_endpoint():
    """handle_bt_capabilities API handler should return topology recommendations."""
    with patch("rpi_dashboard.services.bluetooth.service.get_adapter_recommendations") as mock_recs:
        mock_recs.return_value = {"ok": True, "recommended_audio_adapter": "adapter-1"}
        res = handle_bt_capabilities({})
        assert res["ok"] is True
        assert res["recommended_audio_adapter"] == "adapter-1"


def test_set_phone_role_source_and_sink():
    """set_phone_role should configure source vs sink roles."""
    with patch("rpi_dashboard.services.bluetooth.service._resolve_device", return_value=("adapter-0", "adapter-0/11:22:33:44:55:66")):
        res_source = set_phone_role(adapter_id="adapter-0", device_key="adapter-0/11:22:33:44:55:66", role="source")
        assert res_source["ok"] is True
        assert res_source["role"] == "source"
        assert res_source["target_uuid"] == "0000110a-0000-1000-8000-00805f9b34fb"

        res_sink = set_phone_role(adapter_id="adapter-0", device_key="adapter-0/11:22:33:44:55:66", role="sink")
        assert res_sink["ok"] is True
        assert res_sink["role"] == "sink"
        assert res_sink["target_uuid"] == "0000110b-0000-1000-8000-00805f9b34fb"


def test_handle_bt_phone_role_endpoint():
    """handle_bt_phone_role handler should route query params."""
    with patch("rpi_dashboard.services.bluetooth.service.set_phone_role") as mock_set:
        mock_set.return_value = {"ok": True, "role": "source"}
        res = handle_bt_phone_role({"role": "source", "adapter_id": "adapter-0", "device_key": "adapter-0/11:22:33:44:55:66"})
        assert res["ok"] is True
        assert res["role"] == "source"

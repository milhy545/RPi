from rpi_dashboard.services.bluetooth.capabilities import recommend_adapter_topology, detect_adapter_bus_type

def test_detect_adapter_bus_type_path_fallback():
    assert detect_adapter_bus_type(None, "/org/bluez/hci0") == "uart"
    assert detect_adapter_bus_type(None, "/org/bluez/hci1") == "usb"
    assert detect_adapter_bus_type(None, "/org/bluez/usb_bt") == "usb"
    assert detect_adapter_bus_type(None, "") == "unknown"

def test_recommend_adapter_topology():
    adapters = [
        {"id": "adapter-0", "index": 0, "bluez_path": "/org/bluez/hci0"},
        {"id": "adapter-1", "index": 1, "bluez_path": "/org/bluez/hci1"},
    ]
    rec = recommend_adapter_topology(adapters)
    assert rec["ok"] is True
    assert rec["recommended_audio_adapter"] == "adapter-0"
    assert rec["recommended_io_adapter"] == "adapter-1"
    assert rec["warning"] is None

"""Tests for devices service module."""

from unittest.mock import patch, MagicMock


def test_bt_device_type_audio():
    """Test Bluetooth device type detection for audio."""
    from rpi_dashboard.services.devices import _bt_device_type
    assert _bt_device_type("Speaker Pro") == "audio_output"
    assert _bt_device_type("JBL Soundbar") == "audio_output"
    assert _bt_device_type("Headphone Max") == "audio_output"


def test_bt_device_type_gamepad():
    """Test Bluetooth device type detection for gamepad."""
    from rpi_dashboard.services.devices import _bt_device_type
    assert _bt_device_type("Xbox Controller") == "gamepad"
    assert _bt_device_type("Gamepad Pro") == "gamepad"


def test_bt_device_kind_xbox_controller():
    """Test UI role detection for Xbox controllers."""
    from rpi_dashboard.services.devices import _bt_device_kind
    assert _bt_device_kind("Xbox Wireless Controller") == "xbox_controller"
    assert _bt_device_kind("8BitDo Gamepad") == "gamepad"
    assert _bt_device_kind("JBL Soundbar") == "speaker"


def test_bt_device_type_input():
    """Test Bluetooth device type detection for input."""
    from rpi_dashboard.services.devices import _bt_device_type
    assert _bt_device_type("Keyboard Pro") == "input"
    assert _bt_device_type("Mouse Wireless") == "input"


def test_bt_device_type_unknown():
    """Test Bluetooth device type detection for unknown."""
    from rpi_dashboard.services.devices import _bt_device_type
    assert _bt_device_type("Some Device") == "unknown"


def test_wifi_status_unavailable():
    """Test WiFi status when unavailable."""
    from rpi_dashboard.services.devices import wifi_status
    with patch("rpi_dashboard.services.devices._run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        result = wifi_status()
        assert result["available"] is False


def test_wifi_scan():
    """Test WiFi scan."""
    from rpi_dashboard.services.devices import wifi_scan
    with patch("rpi_dashboard.services.devices._run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="MyNetwork:85:WPA2\nOtherNet:70:WPA\n"
        )
        result = wifi_scan()
        assert result["ok"] is True
        assert len(result["networks"]) == 2


def test_bluetooth_pair():
    """Test Bluetooth pairing."""
    from rpi_dashboard.services.devices import bluetooth_pair
    with patch("rpi_dashboard.services.devices._run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="Pairing successful")
        result = bluetooth_pair("00:00:00:00:00:00")
        assert result["ok"] is True


def test_bluetooth_trust():
    """Test Bluetooth trust."""
    from rpi_dashboard.services.devices import bluetooth_trust
    with patch("rpi_dashboard.services.devices._run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="Trust successful")
        result = bluetooth_trust("00:00:00:00:00:00")
        assert result["ok"] is True


def test_devices_state():
    """Test devices state."""
    from rpi_dashboard.services.devices import devices_state
    with patch("rpi_dashboard.services.devices._bt_paired_devices", return_value=[]):
        with patch("rpi_dashboard.services.devices._bt_scanned_devices", return_value=[]):
            with patch("rpi_dashboard.services.devices.wifi_status", return_value={"available": False}):
                result = devices_state()
                assert "bluetooth" in result
                assert "wifi" in result
                assert result["ok"] is True


def test_bluetooth_devices_normalizes_state():
    """Test Bluetooth paired/scanned normalization."""
    from rpi_dashboard.services.devices import bluetooth_devices

    def fake_run(cmd, t=5):
        if cmd == ["bluetoothctl", "devices", "Paired"]:
            return MagicMock(returncode=0, stdout="Device AA:BB Xbox Wireless Controller\n")
        if cmd == ["bluetoothctl", "devices", "Scanned"]:
            return MagicMock(returncode=0, stdout="Device CC:DD JBL Soundbar\n")
        if cmd == ["bluetoothctl", "info", "AA:BB"]:
            return MagicMock(returncode=0, stdout="Paired: yes\nConnected: yes\nTrusted: yes\n")
        if cmd == ["bluetoothctl", "info", "CC:DD"]:
            return MagicMock(returncode=0, stdout="Paired: no\nConnected: no\nTrusted: no\n")
        return MagicMock(returncode=0, stdout="")

    with patch("rpi_dashboard.services.devices._run", side_effect=fake_run):
        result = bluetooth_devices()
        assert result[0]["kind"] == "xbox_controller"
        assert result[0]["connected"] is True
        assert result[1]["kind"] == "speaker"
        assert result[1]["paired"] is False


def test_bluetooth_controller_status_reports_ready():
    """Test Xbox/Steam Link readiness summary."""
    from rpi_dashboard.services.devices import bluetooth_controller_status

    devices = [{
        "mac": "AA:BB",
        "name": "Xbox Wireless Controller",
        "kind": "xbox_controller",
        "type": "gamepad",
        "connected": True,
    }]
    with patch("rpi_dashboard.services.devices.shutil.which", return_value="/usr/bin/steamlink"):
        with patch("rpi_dashboard.services.devices._loaded_modules", return_value=["uhid"]):
            with patch("rpi_dashboard.services.devices._input_device_names", return_value=["Xbox Wireless Controller"]):
                result = bluetooth_controller_status(devices)
                assert result["ready"] is True
                assert result["steamlink"]["available"] is True
                assert result["modules"]["uhid"] is True

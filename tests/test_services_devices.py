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

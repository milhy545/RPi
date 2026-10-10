"""Tests for fail-closed optional outbound HID control."""

from unittest.mock import patch

from rpi_dashboard.services.bluetooth.hid import hid_transport_status


def test_hid_transport_fails_closed_without_uhid_and_profile():
    with patch("rpi_dashboard.services.bluetooth.hid.Path.exists", return_value=False), patch.dict(
        "os.environ", {}, clear=True
    ):
        status = hid_transport_status()

    assert status["available"] is False
    assert status["enabled_by_default"] is False
    assert "/dev/uhid is unavailable" in status["blockers"]
    assert "AVRCP" in status["safe_alternative"]

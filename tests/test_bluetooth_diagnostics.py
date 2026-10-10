"""Tests for bounded Bluetooth log failure disposition."""

from unittest.mock import MagicMock, patch

from rpi_dashboard.services.bluetooth.diagnostics import analyze_log_text
from rpi_dashboard.services.bluetooth.diagnostics import collect_diagnostics


def test_known_log_classes_map_to_actionable_layers_and_verification():
    text = """
    kernel: Bluetooth: hci0: command 0x0401 tx timeout
    kernel: Bluetooth: hci1: security requested but not available
    wireplumber: a2dp profile Device or resource busy
    pipewire: pw.node xrun detected
    bluetoothd: HFP connection refused
    kernel: xbox gatt report map failed
    """

    classes = analyze_log_text(text)
    by_id = {item["id"]: item for item in classes}

    assert {
        "hci_command_timeout",
        "security_unavailable",
        "a2dp_profile_busy",
        "pipewire_xrun",
        "hfp_connection_refused",
        "xbox_hid_gatt",
    } <= set(by_id)
    assert by_id["security_unavailable"]["layer"] == "link security"
    assert all(item["mitigation"] and item["verification"] for item in classes)


def test_failure_samples_and_history_are_bounded():
    text = "\n".join(f"pipewire: xrun {index}" for index in range(20))

    result = analyze_log_text(text)

    assert result[0]["count"] == 20
    assert len(result[0]["samples"]) == 3
    assert result[0]["samples"][-1].endswith("19")


def test_collection_survives_unavailable_user_journal():
    success = MagicMock(returncode=0, stdout="Bluetooth: hci0 command tx timeout\n", stderr="")
    failure = MagicMock(returncode=1, stdout="", stderr="No user bus")
    version = MagicMock(returncode=0, stdout="5.66\n", stderr="")
    with patch(
        "rpi_dashboard.services.bluetooth.diagnostics._run",
        side_effect=[success, success, failure, version, version, version],
    ), patch(
        "rpi_dashboard.services.bluetooth.diagnostics._adapter_statistics",
        return_value=[],
    ), patch(
        "rpi_dashboard.services.bluetooth.diagnostics._resource_snapshot",
        return_value={"process_rss": "10 kB"},
    ):
        result = collect_diagnostics()

    assert result["ok"] is True
    assert result["log_errors"] == ["No user bus"]
    assert result["failure_classes"][0]["id"] == "hci_command_timeout"
    assert result["resources"]["process_rss"] == "10 kB"

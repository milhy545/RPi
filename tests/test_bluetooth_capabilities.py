"""Bluetooth profile capability mapping tests."""

from rpi_dashboard.services.bluetooth.capabilities import capability_summary
from rpi_dashboard.services.bluetooth.capabilities import pc_capability_matrix


def test_capabilities_are_derived_from_remote_uuids():
    summary = capability_summary(
        (
            "0000110A-0000-1000-8000-00805F9B34FB",
            "00001105-0000-1000-8000-00805F9B34FB",
            "00001124-0000-1000-8000-00805F9B34FB",
            "0000180F-0000-1000-8000-00805F9B34FB",
        )
    )

    assert summary["audio"]["receive"] is True
    assert summary["file_transfer"]["object_push"] is True
    assert summary["control"]["hid"] is True
    assert summary["telemetry"]["battery"] is True
    assert {profile["id"] for profile in summary["profiles"]} >= {
        "a2dp-source",
        "opp",
        "hid",
        "battery",
    }


def test_unknown_uuids_are_preserved_without_claiming_support():
    uuid = "12345678-1234-5678-1234-56789abcdef0"
    summary = capability_summary((uuid,))

    assert summary["profiles"] == []
    assert summary["unknown_uuids"] == [uuid]


def test_pc_matrix_uses_conditional_outcomes_and_prerequisites():
    matrix = pc_capability_matrix()

    assert set(matrix) == {"windows", "linux"}
    assert matrix["windows"]["a2dp_sink"]["status"] == "conditional"
    assert matrix["linux"]["opp"]["status"] == "conditional"
    assert matrix["windows"]["hid_host"]["status"] == "conditional"
    assert all(item["prerequisite"] for platform in matrix.values() for item in platform.values())

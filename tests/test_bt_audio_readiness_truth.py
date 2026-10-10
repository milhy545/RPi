"""Unit tests for BT audio readiness truth, dynamic sink correlation, and error handling."""

from unittest.mock import patch
from rpi_dashboard.services.bluetooth import service as bt_service


def test_bt_readiness_no_connected_bt_audio_device():
    """Verify readiness returns N/A (None) for audio steps when no BT audio device is connected."""
    mock_state = {
        "devices": [
            {
                "address": "00:11:22:33:44:55",
                "connected": False,
                "paired": True,
                "kind": "speaker",
                "uuids": ["0000110b-0000-1000-8000-00805f9b34fb"],
            }
        ],
        "diagnostics": {
            "soundbar": {
                "steps": [
                    {"id": "adapter", "state": True},
                    {"id": "known", "state": True},
                    {"id": "pipewire_sink", "state": None},
                    {"id": "route", "state": None},
                ]
            }
        },
    }
    with patch("rpi_dashboard.services.audio.audio_state", return_value={"sinks": [], "default_sink": "hdmi"}):
        bt_service._enrich_soundbar_audio_readiness(mock_state)
        steps = {s["id"]: s for s in mock_state["diagnostics"]["soundbar"]["steps"]}
        assert steps["pipewire_sink"]["state"] is None
        assert "Not applicable" in steps["pipewire_sink"]["reason"]
        assert steps["route"]["state"] is None
        assert mock_state["diagnostics"]["soundbar"]["ready"] is True


def test_bt_readiness_dynamic_sink_identity_and_default_route():
    """Verify connected BT audio device matches PipeWire sink by MAC and marks route PASS when default."""
    mock_state = {
        "devices": [
            {
                "address": "E4:7B:22:11:44:55",
                "connected": True,
                "paired": True,
                "kind": "speaker",
                "uuids": ["0000110b-0000-1000-8000-00805f9b34fb"],
            }
        ],
        "diagnostics": {
            "soundbar": {
                "steps": [
                    {"id": "adapter", "state": True},
                    {"id": "pipewire_sink", "state": None},
                    {"id": "route", "state": None},
                ]
            }
        },
    }
    mock_audio = {
        "sinks": [
            {"name": "bluez_output.E4_7B_22_11_44_55.a2dp_sink", "id": 56},
            {"name": "alsa_output.platform", "id": 41},
        ],
        "default_sink": "bluez_output.E4_7B_22_11_44_55.a2dp_sink",
        "sink_inputs": [],
        "routes": {},
    }
    with patch("rpi_dashboard.services.audio.audio_state", return_value=mock_audio):
        bt_service._enrich_soundbar_audio_readiness(mock_state)
        steps = {s["id"]: s for s in mock_state["diagnostics"]["soundbar"]["steps"]}
        assert steps["pipewire_sink"]["state"] is True
        assert "PipeWire sink present" in steps["pipewire_sink"]["reason"]
        assert steps["route"]["state"] is True
        assert "default route" in steps["route"]["reason"]
        assert mock_state["diagnostics"]["soundbar"]["ready"] is True


def test_bt_readiness_active_stream_routed_to_bt_sink():
    """Verify route step passes when an active stream is routed to the BT sink even if not default."""
    mock_state = {
        "devices": [
            {
                "address": "00:11:22:33:44:55",
                "connected": True,
                "paired": True,
                "kind": "headphones",
                "uuids": ["0000110b-0000-1000-8000-00805f9b34fb"],
            }
        ],
        "diagnostics": {
            "soundbar": {
                "steps": [
                    {"id": "pipewire_sink", "state": None},
                    {"id": "route", "state": None},
                ]
            }
        },
    }
    mock_audio = {
        "sinks": [
            {"name": "bluez_output.00_11_22_33_44_55.a2dp_sink", "id": 57},
        ],
        "default_sink": "alsa_output.platform",
        "sink_inputs": [{"sink": "bluez_output.00_11_22_33_44_55.a2dp_sink"}],
        "routes": {},
    }
    with patch("rpi_dashboard.services.audio.audio_state", return_value=mock_audio):
        bt_service._enrich_soundbar_audio_readiness(mock_state)
        steps = {s["id"]: s for s in mock_state["diagnostics"]["soundbar"]["steps"]}
        assert steps["pipewire_sink"]["state"] is True
        assert steps["route"]["state"] is True
        assert "Active stream" in steps["route"]["reason"]


def test_bt_readiness_optional_loopback_inactive_not_blocker():
    """Verify inactive optional loopback alone is not a blocker if default route is set."""
    mock_state = {
        "devices": [
            {
                "address": "00:11:22:33:44:55",
                "connected": True,
                "paired": True,
                "kind": "speaker",
                "uuids": [],
            }
        ],
        "diagnostics": {
            "soundbar": {
                "steps": [
                    {"id": "pipewire_sink", "state": None},
                    {"id": "route", "state": None},
                ]
            }
        },
    }
    mock_audio = {
        "sinks": [{"name": "bluez_output.00_11_22_33_44_55.a2dp_sink", "id": 57}],
        "default_sink": "bluez_output.00_11_22_33_44_55.a2dp_sink",
        "sink_inputs": [],
        "routes": {"alexa_to_bt": {"on": False}},
    }
    with patch("rpi_dashboard.services.audio.audio_state", return_value=mock_audio):
        bt_service._enrich_soundbar_audio_readiness(mock_state)
        steps = {s["id"]: s for s in mock_state["diagnostics"]["soundbar"]["steps"]}
        assert steps["route"]["state"] is True
        assert mock_state["diagnostics"]["soundbar"]["ready"] is True


def test_bt_readiness_audio_state_unavailable_returns_unknown():
    """Verify audio state failure marks readiness as degraded/unknown (None) without crashing."""
    mock_state = {
        "devices": [{"address": "00:11:22:33:44:55", "connected": True, "kind": "speaker"}],
        "diagnostics": {
            "soundbar": {
                "steps": [
                    {"id": "pipewire_sink", "state": None},
                    {"id": "route", "state": None},
                ]
            }
        },
    }
    with patch("rpi_dashboard.services.audio.audio_state", side_effect=RuntimeError("Command timeout")):
        bt_service._enrich_soundbar_audio_readiness(mock_state)
        steps = {s["id"]: s for s in mock_state["diagnostics"]["soundbar"]["steps"]}
        assert steps["pipewire_sink"]["state"] is None
        assert "unavailable" in steps["pipewire_sink"]["reason"]
        assert steps["route"]["state"] is None
        assert mock_state["diagnostics"]["soundbar"]["ready"] is False


def test_bt_readiness_fuzzed_identifiers_handled_gracefully():
    """Verify fuzzed / malformed MAC addresses and sink names do not crash parser."""
    mock_state = {
        "devices": [
            {"address": "MALFORMED_MAC_123!@#", "connected": True, "kind": "speaker", "uuids": []}
        ],
        "diagnostics": {
            "soundbar": {
                "steps": [
                    {"id": "pipewire_sink", "state": None},
                    {"id": "route", "state": None},
                ]
            }
        },
    }
    mock_audio = {
        "sinks": [{"name": "bluez_output.MALFORMED_123.sink", "id": 999}],
        "default_sink": "bluez_output.MALFORMED_123.sink",
        "sink_inputs": [],
        "routes": {},
    }
    with patch("rpi_dashboard.services.audio.audio_state", return_value=mock_audio):
        bt_service._enrich_soundbar_audio_readiness(mock_state)
        steps = {s["id"]: s for s in mock_state["diagnostics"]["soundbar"]["steps"]}
        assert steps["pipewire_sink"]["state"] in (True, False)
        assert steps["route"]["state"] in (True, False)

"""Tests for audio service module."""

import pytest
from unittest.mock import patch, MagicMock


def test_classify_sink_hdmi():
    """Test HDMI sink classification."""
    from rpi_dashboard.services.audio import _classify_sink
    assert _classify_sink("alsa_output.platform-hdmi-audio.0.hdmi-stereo") == "hdmi"
    assert _classify_sink("HDMI Output") == "hdmi"


def test_classify_sink_bluetooth():
    """Test Bluetooth sink classification."""
    from rpi_dashboard.services.audio import _classify_sink
    assert _classify_sink("bluez_output.00_00_00_00_00_00.a2dp_sink") == "bt"
    assert _classify_sink("bluez_sink") == "bt"


def test_classify_sink_dlna():
    """Test DLNA sink classification."""
    from rpi_dashboard.services.audio import _classify_sink
    assert _classify_sink("gmrender-output") == "dlna_output"
    assert _classify_sink("gmediarender-sink") == "dlna_output"


def test_classify_sink_usb():
    """Test USB sink classification."""
    from rpi_dashboard.services.audio import _classify_sink
    assert _classify_sink("usb-audio-output") == "usb_output"


def test_classify_source_monitor():
    """Test monitor source classification."""
    from rpi_dashboard.services.audio import _classify_source
    assert _classify_source("monitor of hdmi") == "monitor"


def test_classify_source_usb():
    """Test USB source classification."""
    from rpi_dashboard.services.audio import _classify_source
    # USB Alexa source has a specific prefix
    from rpi_dashboard.services.audio import USB_ALEXA_SRC
    assert _classify_source(USB_ALEXA_SRC) == "usb_input"


def test_load_audio_latency_default():
    """Test loading default audio latency."""
    from rpi_dashboard.services.audio import _load_audio_latency
    with patch("os.path.exists", return_value=False):
        result = _load_audio_latency()
        assert result == {"dlna_output_offset_ms": 0, "default_latency_ms": 0}


def test_audio_set_volume_clamp():
    """Test volume clamping."""
    from rpi_dashboard.services.audio import audio_set_volume
    with patch("rpi_dashboard.services.audio._run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = audio_set_volume("sink", "test", 200)
        assert result["volume"] == 150  # Clamped to max
        
        result = audio_set_volume("sink", "test", -10)
        assert result["volume"] == 0  # Clamped to min


def test_audio_set_latency():
    """Test setting audio latency."""
    from rpi_dashboard.services.audio import audio_set_latency
    with patch("rpi_dashboard.services.audio._save_audio_latency") as mock_save:
        with patch("rpi_dashboard.services.audio._apply_dlna_delay"):
            result = audio_set_latency("dlna_output_offset_ms", 100)
            assert result["ok"] is True
            mock_save.assert_called_once()


def test_get_audio_matrix():
    """Test getting audio matrix."""
    from rpi_dashboard.services.audio import get_audio_matrix
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout='[{"type": "PipeWire:Interface:Node", "id": 1, "info": {"props": {"node.name": "test", "media.class": "Audio/Sink"}}}]',
            returncode=0
        )
        result = get_audio_matrix()
        assert "nodes" in result
        assert "links" in result


def test_diagnose_bt_audio_stutter():
    """Test BT audio stutter diagnostics."""
    from rpi_dashboard.services.audio import diagnose_bt_audio_stutter
    with patch("rpi_dashboard.services.audio._run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        result = diagnose_bt_audio_stutter()
        assert "pipewire_quantum" in result
        assert "recommendations" in result


def test_fix_bt_audio_stutter():
    """Test BT audio stutter fix."""
    from rpi_dashboard.services.audio import fix_bt_audio_stutter
    with patch("rpi_dashboard.services.audio._run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = fix_bt_audio_stutter()
        assert "ok" in result
        assert "fixes_applied" in result

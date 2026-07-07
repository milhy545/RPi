import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rpi_dashboard.tui.formatting import (
    badge,
    human_audio_sink,
    human_bt_device,
    truncate_middle,
)


def test_badge_is_ascii_and_uppercase():
    assert badge("connected") == "[CONNECTED]"
    assert badge("active") == "[ACTIVE]"


def test_truncate_middle_keeps_both_ends():
    assert truncate_middle("alsa_output.platform-3f902000.hdmi.hdmi-stereo", 28) == "alsa_output.pl...hdmi-stereo"


def test_human_audio_sink_prefers_readable_name():
    item = human_audio_sink("alsa_output.platform-3f902000.hdmi.hdmi-stereo", default=True)
    assert item.primary == "TV HDMI"
    assert item.status == "[ACTIVE]"
    assert "alsa_output" in item.detail


def test_human_bt_device_uses_name_and_mac_detail():
    item = human_bt_device("Device 24:4B:03:92:0B:8C [Samsung] Soundbar J-Series", connected=True)
    assert item.primary == "[Samsung] Soundbar J-Series"
    assert item.status == "[CONNECTED]"
    assert item.detail == "24:4B:03:92:0B:8C"

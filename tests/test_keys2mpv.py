import os
import sys
from unittest.mock import mock_open, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from keys2mpv import KEYMAP, SOCKETS
from rpi_dashboard.services.input_devices import (
    find_all_input_devices_by_name_pattern,
    find_keyboard_device,
)


def test_find_keyboard_device_by_id(monkeypatch):
    monkeypatch.setattr("glob.glob", lambda pat: ["/dev/input/by-id/usb-test-kbd"])
    monkeypatch.setattr("os.path.exists", lambda path: True)
    assert find_keyboard_device() == "/dev/input/by-id/usb-test-kbd"


def test_find_keyboard_device_by_name(monkeypatch):
    # by-id returns nothing
    monkeypatch.setattr(
        "glob.glob",
        lambda pat: [] if "by-id" in pat else ["/sys/class/input/event3"],
    )
    monkeypatch.setattr("os.path.isfile", lambda path: True)
    monkeypatch.setattr("os.path.exists", lambda path: True)

    m = mock_open(read_data="Standard USB Keyboard\n")
    with patch("builtins.open", m):
        dev = find_keyboard_device()
        assert dev == "/dev/input/event3"


def test_find_all_input_devices_by_name_pattern(monkeypatch):
    monkeypatch.setattr(
        "glob.glob",
        lambda pat: ["/sys/class/input/event1", "/sys/class/input/event2"],
    )
    monkeypatch.setattr("os.path.isfile", lambda path: True)
    monkeypatch.setattr("os.path.exists", lambda path: True)

    def custom_open(file, *args, **kwargs):
        if "event1" in file:
            return mock_open(read_data="Xbox Wireless Controller\n")()
        return mock_open(read_data="USB Mouse\n")()

    with patch("builtins.open", side_effect=custom_open):
        devices = find_all_input_devices_by_name_pattern("xbox")
        assert devices == ["/dev/input/event1"]


def test_keys2mpv_keymap_mute():
    assert 113 in KEYMAP
    cmd, label = KEYMAP[113]
    assert cmd == ["cycle", "mute"]
    assert label == "🔇  Mute"


def test_keys2mpv_sockets():
    assert "/tmp/rpi-mpv.sock" in SOCKETS or os.environ.get("MPV_SOCKET") in SOCKETS

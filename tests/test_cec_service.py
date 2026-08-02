"""CEC service contracts with the external binaries mocked."""

from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import pytest

from rpi_dashboard.services import cec


def test_cec_cmd_and_scan_success(monkeypatch: pytest.MonkeyPatch) -> None:
    proc = MagicMock(returncode=0)
    proc.communicate.return_value = ("TV response", "")
    monkeypatch.setattr(cec.subprocess, "Popen", MagicMock(return_value=proc))

    assert cec.cec_cmd("on 0") == {"ok": True, "output": "TV response"}
    proc.communicate.assert_called_once_with(input="on 0\n", timeout=5)

    run = MagicMock(returncode=0, stdout="device 0\ndevice 1\n")
    monkeypatch.setattr(cec.subprocess, "run", MagicMock(return_value=run))
    result = cec.cec_scan()
    assert result["devices"] == ["device 0", "device 1"]


def test_cec_external_failures_are_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cec.subprocess, "Popen", MagicMock(side_effect=OSError("missing")))
    monkeypatch.setattr(cec.subprocess, "run", MagicMock(side_effect=OSError("missing")))
    assert cec.cec_cmd("on 0") == {"ok": False, "error": "missing"}
    assert cec.cec_scan() == {"ok": False, "error": "missing"}
    assert cec.cec_physical_address() is None


@pytest.mark.parametrize(
    ("function", "command"),
    [
        (cec.cec_power_on, "on 0"),
        (cec.cec_power_off, "standby 0"),
        (cec.cec_volume_up, "volup"),
        (cec.cec_volume_down, "voldown"),
        (cec.cec_mute, "mute"),
        (cec.cec_up, "up"),
        (cec.cec_down, "down"),
        (cec.cec_left, "left"),
        (cec.cec_right, "right"),
        (cec.cec_select, "select"),
        (cec.cec_back, "back"),
        (cec.cec_menu, "menu"),
        (cec.cec_input_hdmi1, "input 1"),
        (cec.cec_input_hdmi2, "input 2"),
        (cec.cec_input_hdmi3, "input 3"),
        (cec.cec_active_source, "active_source"),
    ],
)
def test_cec_convenience_commands(
    monkeypatch: pytest.MonkeyPatch,
    function: Callable[[], dict[str, Any]],
    command: str,
) -> None:
    call = MagicMock(return_value={"ok": True})
    monkeypatch.setattr(cec, "cec_cmd", call)
    assert function() == {"ok": True}
    call.assert_called_once_with(command)


def test_bridge_lifecycle_terminates_then_kills_if_needed(monkeypatch: pytest.MonkeyPatch) -> None:
    old = MagicMock(pid=10)
    old.poll.return_value = None
    old.wait.side_effect = TimeoutError("stuck")
    cec._CEC_BRIDGE = old
    cec.cec_bridge_stop()
    old.terminate.assert_called_once_with()
    old.kill.assert_called_once_with()

    new = MagicMock(pid=20)
    new.poll.return_value = None
    popen = MagicMock(return_value=new)
    monkeypatch.setattr(cec.subprocess, "Popen", popen)
    result = cec.cec_bridge_start()
    assert result == {"ok": True, "pid": 20}
    assert cec.cec_bridge_status() == {"on": True, "pid": 20}
    cec.cec_bridge_stop()


def test_physical_address_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    proc = MagicMock()
    proc.communicate.return_value = ("notice\nphysical address: 1.0.0.0\n", "")
    monkeypatch.setattr(cec.subprocess, "Popen", MagicMock(return_value=proc))
    assert cec.cec_physical_address() == "1.0.0.0"

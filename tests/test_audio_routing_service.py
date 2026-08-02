"""Behavior tests for high-level audio routing decisions."""

from unittest.mock import MagicMock

import pytest

from rpi_dashboard.services import audio_routing


def result(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    return MagicMock(returncode=returncode, stdout=stdout, stderr=stderr)


def test_keepalive_actions(monkeypatch: pytest.MonkeyPatch) -> None:
    start = MagicMock(return_value=True)
    stop = MagicMock()
    stop_orphans = MagicMock(return_value=2)
    monkeypatch.setattr(audio_routing, "_keepalive_start", start)
    monkeypatch.setattr(audio_routing, "_keepalive_stop", stop)
    monkeypatch.setattr(audio_routing, "_stop_keepalive_orphans", stop_orphans)
    monkeypatch.setattr(audio_routing, "_keepalive_status", MagicMock(return_value=["hdmi"]))
    monkeypatch.setattr(audio_routing, "_keepalive_orphans", MagicMock(return_value=[]))

    assert audio_routing.audio_keepalive("start", "hdmi")["ok"] is True
    start.assert_called_once_with("hdmi")
    assert audio_routing.audio_keepalive("stop", "hdmi")["ok"] is True
    stop.assert_called_with("hdmi")
    stopped = audio_routing.audio_keepalive("stop_all")
    assert stopped["killed"] == 2
    stop.assert_called_with()
    assert audio_routing.audio_keepalive("status")["active"] == ["hdmi"]


@pytest.mark.parametrize(
    ("target", "sinks", "expected"),
    [
        ("bt", ["bluez_sink.A"], "bluez_sink.A"),
        ("hdmi", ["alsa_output.hdmi"], "alsa_output.hdmi"),
        ("dlna", ["uuid_renderer", "uuid_lg"], "uuid_renderer"),
        ("unknown", ["alsa_output.hdmi"], None),
    ],
)
def test_choose_output_sink(
    monkeypatch: pytest.MonkeyPatch,
    target: str,
    sinks: list[str],
    expected: str | None,
) -> None:
    monkeypatch.setattr(audio_routing, "_pactl_lines", lambda _kind: [{"name": s} for s in sinks])
    assert audio_routing._choose_output_sink(target) == expected


def test_route_output_sets_sink_and_stops_dlna(monkeypatch: pytest.MonkeyPatch) -> None:
    run = MagicMock(return_value=result(stdout="ok"))
    monkeypatch.setattr(audio_routing, "_run", run)
    monkeypatch.setattr(audio_routing, "_pa_dlna_running", MagicMock(return_value=True))
    monkeypatch.setattr(audio_routing, "_choose_output_sink", MagicMock(return_value="bluez_sink.A"))

    routed = audio_routing.audio_route_output("BT")
    assert routed["ok"] is True
    assert routed["sink"] == "bluez_sink.A"
    assert run.call_args_list[0].args[0] == ["pkill", "-f", "pa-dlna"]
    assert run.call_args_list[1].args[0] == ["pactl", "set-default-sink", "bluez_sink.A"]


def test_route_output_reports_invalid_and_missing_sinks(monkeypatch: pytest.MonkeyPatch) -> None:
    assert audio_routing.audio_route_output("invalid")["ok"] is False
    monkeypatch.setattr(audio_routing, "_choose_output_sink", MagicMock(return_value=None))
    monkeypatch.setattr(audio_routing, "_pa_dlna_running", MagicMock(return_value=False))
    monkeypatch.setattr(
        audio_routing.subprocess,
        "run",
        MagicMock(return_value=result(stdout="Device AA:BB Soundbar")),
    )
    assert "Paired" in audio_routing.audio_route_output("bt")["result"]
    assert audio_routing.audio_route_output("hdmi")["ok"] is False


def test_toggle_mute_validates_and_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    assert audio_routing.audio_toggle_mute("", "")["ok"] is False
    run = MagicMock(return_value=result())
    monkeypatch.setattr(audio_routing, "_run", run)
    assert audio_routing.audio_toggle_mute("sink", "hdmi")["ok"] is True
    run.assert_called_once_with(["pactl", "set-sink-mute", "hdmi", "toggle"], t=5)


def test_retarget_alexa_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audio_routing.time, "sleep", MagicMock())
    monkeypatch.setattr(audio_routing, "_alexa_loopback_running", MagicMock(return_value=(False, None, None)))
    assert audio_routing._retarget_alexa()["ok"] is False

    monkeypatch.setattr(audio_routing, "_alexa_loopback_running", MagicMock(return_value=(True, "hdmi", "7")))
    monkeypatch.setattr(audio_routing, "_resolve_alexa_target", MagicMock(return_value="hdmi"))
    assert audio_routing._retarget_alexa()["unchanged"] is True

    monkeypatch.setattr(audio_routing, "_resolve_alexa_target", MagicMock(return_value="bluez"))
    monkeypatch.setattr(audio_routing, "_stop_loopback", MagicMock())
    monkeypatch.setattr(audio_routing, "_start_loopback", MagicMock(return_value="8"))
    changed = audio_routing._retarget_alexa()
    assert changed["new_target"] == "bluez"
    assert changed["module_id"] == "8"


def test_dlnain_start_stop_and_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audio_routing, "_dlnain_loopback_running", MagicMock(return_value=(False, None)))
    monkeypatch.setattr(audio_routing, "_pactl_lines", MagicMock(return_value=[{"name": "gmediarender.monitor"}]))
    monkeypatch.setattr(audio_routing, "_resolve_dlnain_target", MagicMock(return_value="hdmi"))
    monkeypatch.setattr(audio_routing, "_start_loopback", MagicMock(return_value="9"))
    assert audio_routing._dlnain_start()["module_id"] == "9"

    monkeypatch.setattr(audio_routing, "_dlnain_loopback_running", MagicMock(return_value=(True, "gmediarender.monitor")))
    monkeypatch.setattr(audio_routing, "_stop_loopback_by_source", MagicMock(return_value=True))
    assert audio_routing._dlnain_stop()["ok"] is True

    config = {"mode": "follow", "manual_sink": None}
    save = MagicMock()
    monkeypatch.setattr(audio_routing, "_load_dlnain_mode", MagicMock(return_value=config))
    monkeypatch.setattr(audio_routing, "_save_dlnain_mode", save)
    assert audio_routing.dlnain_set_mode("bad")["ok"] is False
    assert audio_routing.dlnain_set_mode("manual")["mode"] == "manual"
    assert audio_routing.dlnain_set_target("")["ok"] is False
    assert audio_routing.dlnain_set_target("bluez")["manual_sink"] == "bluez"


def test_alexa_route_status_stop_start_and_reset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audio_routing.audio, "_get_default_sink", MagicMock(return_value="hdmi"))
    monkeypatch.setattr(audio_routing, "_alexa_loopback_running", MagicMock(return_value=(True, "hdmi", "3")))
    assert audio_routing.audio_route_alexa_bt("status")["on"] is True

    monkeypatch.setattr(audio_routing, "_loopback_module_id", MagicMock(return_value="3"))
    run = MagicMock(return_value=result(stdout="4"))
    monkeypatch.setattr(audio_routing, "_run", run)
    assert audio_routing.audio_route_alexa_bt("stop")["on"] is False
    assert audio_routing.audio_route_alexa_bt("start")["already"] is True

    monkeypatch.setattr(audio_routing, "_audio_matrix_reset", MagicMock(return_value={"ok": True}))
    assert audio_routing.audio_route_alexa_bt("reset") == {"ok": True}
    assert audio_routing.audio_route_alexa_bt("bad")["ok"] is False

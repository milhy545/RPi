"""Behavior contracts for API handlers without touching real hardware."""

from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import pytest

from rpi_dashboard.api import handlers


def q(**values: object) -> dict[str, list[str]]:
    return {key: [str(value)] for key, value in values.items()}


@pytest.mark.parametrize(
    ("handler", "query", "service", "method", "args"),
    [
        (handlers.handle_audio_default_sink, q(name="hdmi"), handlers.audio, "audio_set_default", ("hdmi",)),
        (handlers.handle_audio_volume, q(kind="sink", name="hdmi", volume=42), handlers.audio, "audio_set_volume", ("sink", "hdmi", 42)),
        (handlers.handle_audio_volume_global, q(volume=70), handlers.audio, "set_global_master_volume", (70,)),
        (handlers.handle_audio_matrix, {}, handlers.audio, "get_audio_matrix", ()),
        (handlers.handle_audio_matrix_link, q(out="source", **{"in": "sink"}, state=1), handlers.audio, "audio_matrix_link", ("source", "sink", "1")),
        (handlers.handle_audio_latency, q(key="hdmi", value=25), handlers.audio, "audio_set_latency", ("hdmi", 25)),
        (handlers.handle_audio_mute_state, q(kind="sink", name="hdmi", muted="false"), handlers.audio, "audio_set_mute", ("sink", "hdmi", False)),
        (handlers.handle_mpv_play, q(url="https://example.test/v", **{"q": "720", "resume": 1}), handlers.player, "mpv_start", ("https://example.test/v", "720", True)),
        (handlers.handle_mpv_stop, {}, handlers.player, "mpv_stop", ()),
        (handlers.handle_mpv_status, {}, handlers.player, "mpv_st", ()),
        (handlers.handle_mpv_seek, q(position="12.5"), handlers.player, "mpv_seek", (12.5,)),
        (handlers.handle_mpv_volume, q(volume=55), handlers.player, "mpv_volume", (55,)),
        (handlers.handle_mpv_toggle, {}, handlers.player, "mpv_toggle", ()),
        (handlers.handle_mpv_seekabs, q(pos="4.5"), handlers.player, "mpv_seek_absolute", (4.5,)),
        (handlers.handle_mpv_vol, q(d=-5), handlers.player, "mpv_volume_delta", (-5,)),
        (handlers.handle_devices_state, {}, handlers.devices, "devices_state", ()),
        (handlers.handle_devices_legacy, {}, handlers.devices, "devices_legacy_summary", ()),
        (handlers.handle_wifi_status, {}, handlers.devices, "wifi_status", ()),
        (handlers.handle_wifi_scan, {}, handlers.devices, "wifi_scan", ()),
        (handlers.handle_wifi_connect, q(ssid="LAN", password="secret"), handlers.devices, "wifi_connect", ("LAN", "secret")),
        (handlers.handle_cec_scan, {}, handlers.cec, "cec_scan", ()),
        (handlers.handle_cec_send, q(c="tx 10:04"), handlers.cec, "cec_send", ("tx 10:04",)),
        (handlers.handle_cec_key, q(k="up"), handlers.cec, "cec_key", ("up",)),
        (handlers.handle_cec_in, q(n=2), handlers.cec, "cec_input", ("2",)),
        (handlers.handle_terminal_connect, {}, handlers.terminal, "terminal_connect", ()),
        (handlers.handle_terminal_disconnect, {}, handlers.terminal, "terminal_disconnect", ()),
        (handlers.handle_system_stats, {}, handlers.system, "get_system_stats", ()),
        (handlers.handle_system_status, {}, handlers.system, "get_system_status", ()),
        (handlers.handle_system_hw_stats, {}, handlers.system, "get_hw_stats", ()),
        (handlers.handle_system_https_info, {}, handlers.system, "get_https_info", ()),
        (handlers.handle_network_info, {}, handlers.system, "get_network_info", ()),
        (handlers.handle_network_tailscale, {}, handlers.system, "get_tailscale_status", ()),
        (handlers.handle_youtube_cookie_status, {}, handlers.media, "youtube_cookie_status", ()),
        (handlers.handle_youtube_age_check, q(url="https://youtu.be/id"), handlers.media, "youtube_age_check", ("https://youtu.be/id",)),
        (handlers.handle_dlna_connect, {}, handlers.audio_dlna, "audio_connect_dlna", ()),
        (handlers.handle_dlna_disconnect, {}, handlers.audio_dlna, "audio_disconnect_dlna", ()),
        (handlers.handle_dlna_scan, {}, handlers.audio_dlna, "dlna_scan", ()),
        (handlers.handle_dlna_renderer_status, {}, handlers.audio_dlna, "dlna_renderer_status", ()),
        (handlers.handle_dlna_renderer_start, {}, handlers.audio_dlna, "dlna_renderer_start", ()),
        (handlers.handle_dlna_renderer_stop, {}, handlers.audio_dlna, "dlna_renderer_stop", ()),
    ],
)
def test_handlers_delegate_typed_values(
    monkeypatch: pytest.MonkeyPatch,
    handler: Callable[[dict[str, list[str]]], dict[str, Any]],
    query: dict[str, list[str]],
    service: object,
    method: str,
    args: tuple[object, ...],
) -> None:
    call = MagicMock(return_value={"ok": True, "source": method})
    monkeypatch.setattr(service, method, call)

    result = handler(query)

    assert result == {"ok": True, "source": method}
    call.assert_called_once_with(*args)


@pytest.mark.parametrize(
    ("handler", "query", "error"),
    [
        (handlers.handle_audio_default_sink, {}, "name required"),
        (handlers.handle_audio_volume, q(name="hdmi", volume="loud"), "volume must be integer"),
        (handlers.handle_audio_volume_global, q(volume="loud"), "volume must be integer"),
        (handlers.handle_audio_matrix_link, q(out="source"), "out and in required"),
        (handlers.handle_audio_latency, q(key="hdmi", value="late"), "value must be integer"),
        (handlers.handle_mpv_play, {}, "url required"),
        (handlers.handle_mpv_seek, q(position="later"), "position must be number"),
        (handlers.handle_mpv_volume, q(volume="loud"), "volume must be integer"),
        (handlers.handle_mpv_seekabs, q(pos="later"), "pos must be number"),
        (handlers.handle_mpv_vol, q(d="more"), "d must be integer"),
        (handlers.handle_mpv_memory, {}, "url required"),
        (handlers.handle_mpv_memory_clear, {}, "url required"),
        (handlers.handle_wifi_connect, {}, "ssid required"),
        (handlers.handle_cec_send, {}, "no cmd"),
        (handlers.handle_cec_key, {}, "no key"),
    ],
)
def test_handlers_reject_invalid_input(
    handler: Callable[[dict[str, list[str]]], dict[str, Any]],
    query: dict[str, list[str]],
    error: str,
) -> None:
    assert handler(query) == {"ok": False, "error": error}


@pytest.mark.parametrize(
    ("handler", "action", "method"),
    [
        (handlers.handle_cec_power, "on", "cec_power_on"),
        (handlers.handle_cec_power, "off", "cec_power_off"),
        (handlers.handle_cec_nav, "up", "cec_up"),
        (handlers.handle_cec_nav, "down", "cec_down"),
        (handlers.handle_cec_nav, "left", "cec_left"),
        (handlers.handle_cec_nav, "right", "cec_right"),
        (handlers.handle_cec_nav, "select", "cec_select"),
        (handlers.handle_cec_nav, "back", "cec_back"),
        (handlers.handle_cec_nav, "menu", "cec_menu"),
        (handlers.handle_cec_vol, "up", "cec_volume_up"),
        (handlers.handle_cec_vol, "down", "cec_volume_down"),
        (handlers.handle_cec_vol, "mute", "cec_mute"),
    ],
)
def test_cec_action_dispatch(
    monkeypatch: pytest.MonkeyPatch,
    handler: Callable[[dict[str, list[str]]], dict[str, Any]],
    action: str,
    method: str,
) -> None:
    call = MagicMock(return_value={"ok": True})
    monkeypatch.setattr(handlers.cec, method, call)

    assert handler(q(action=action)) == {"ok": True}
    call.assert_called_once_with()


def test_audio_multi_output_normalizes_sink_list(monkeypatch: pytest.MonkeyPatch) -> None:
    call = MagicMock(return_value={"ok": True})
    monkeypatch.setattr(handlers.audio, "audio_multi_output", call)

    handlers.handle_audio_multi_output(q(action="enable", sinks="hdmi, bt ,"))

    call.assert_called_once_with("enable", ["hdmi", "bt"])


def test_audio_state_maps_force_to_keyword(monkeypatch: pytest.MonkeyPatch) -> None:
    call = MagicMock(return_value={"ok": True})
    monkeypatch.setattr(handlers.audio, "audio_state", call)

    assert handlers.handle_audio_state(q(force=1))["ok"] is True
    call.assert_called_once_with(force=True)


def test_bluetooth_discovery_validates_action_and_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    start = MagicMock(return_value={"ok": True})
    stop = MagicMock(return_value={"ok": True})
    monkeypatch.setattr(handlers.bluetooth_service, "start_discovery", start)
    monkeypatch.setattr(handlers.bluetooth_service, "stop_discovery", stop)

    assert handlers.handle_bt_discovery(q(action="start", adapter_id="hci1", seconds=8))["ok"]
    start.assert_called_once_with("hci1", 8)
    assert handlers.handle_bt_discovery(q(action="stop"))["ok"]
    stop.assert_called_once_with(None)
    assert handlers.handle_bt_discovery(q(action="start", seconds="bad"))["code"] == "unsupported"
    assert handlers.handle_bt_discovery(q(action="invalid"))["code"] == "unsupported"


def test_mpv_memory_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(handlers.player, "mpv_memory_for_url", MagicMock(return_value={"position": 4}))
    monkeypatch.setattr(handlers.player, "mpv_memory_clear_for_url", MagicMock(return_value=True))
    monkeypatch.setattr(handlers.player, "mpv_ipc_socket_live", MagicMock(return_value=False))

    assert handlers.handle_mpv_memory(q(url="u"))["memory"] == {"position": 4}
    assert handlers.handle_mpv_memory_clear(q(url="u"))["cleared"] is True
    assert handlers.handle_mpv_memory_save({}) == {"ok": True, "memory": "mpv not running"}


def test_return_config_set_normalizes_form_values(monkeypatch: pytest.MonkeyPatch) -> None:
    update = MagicMock(return_value={"xbox_b_hold_enabled": True})
    monkeypatch.setattr(handlers.return_service, "update_config", update)

    result = handlers.handle_return_config_set({"xbox_b_hold_enabled": ["true"]})

    assert result["ok"] is True
    update.assert_called_once_with({"xbox_b_hold_enabled": "true"})


def test_return_config_set_reports_service_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        handlers.return_service,
        "update_config",
        MagicMock(side_effect=ValueError("invalid duration")),
    )

    assert handlers.handle_return_config_set({}) == {"ok": False, "error": "invalid duration"}

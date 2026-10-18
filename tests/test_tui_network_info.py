"""Regresní testy síťových informací v produkčním TUI."""

from __future__ import annotations

import asyncio
import io
import socket
from types import SimpleNamespace
from typing import Any, cast

import fcntl

import tui


class _FakeSocket:
    def fileno(self) -> int:
        return 7

    def close(self) -> None:
        pass


def _ioctl_result(address: str) -> bytes:
    result = bytearray(256)
    result[20:24] = socket.inet_aton(address)
    return bytes(result)


def test_get_interfaces_info_formats_prefix_and_separate_tailscale_ip(monkeypatch) -> None:
    addresses = {
        ("eth0", 0x8915): "192.0.2.15",
        ("eth0", 0x891B): "255.255.255.0",
        ("tailscale0", 0x8915): "100.64.0.8",
        ("tailscale0", 0x891B): "255.255.255.255",
    }

    def ioctl(_fd: int, request_code: int, request: bytes) -> bytes:
        name = request.split(b"\0", 1)[0].decode()
        return _ioctl_result(addresses[(name, request_code)])

    monkeypatch.setattr(tui.socket, "if_nameindex", lambda: [(1, "lo"), (2, "eth0"), (3, "tailscale0")])
    monkeypatch.setattr(tui.socket, "socket", lambda *_args, **_kwargs: _FakeSocket())
    monkeypatch.setattr(fcntl, "ioctl", ioctl)

    dashboard = cast(tui.RPiDashboard, SimpleNamespace())
    result = tui.RPiDashboard.get_interfaces_info(dashboard)

    assert result == ("eth0: 192.0.2.15/24 | tailscale0: 100.64.0.8/32", "100.64.0.8")


def test_get_interfaces_info_keeps_address_when_netmask_lookup_fails(monkeypatch) -> None:
    def ioctl(_fd: int, request_code: int, _request: bytes) -> bytes:
        if request_code == 0x891B:
            raise OSError("netmask unavailable")
        return _ioctl_result("192.0.2.20")

    monkeypatch.setattr(tui.socket, "if_nameindex", lambda: [(2, "eth0")])
    monkeypatch.setattr(tui.socket, "socket", lambda *_args, **_kwargs: _FakeSocket())
    monkeypatch.setattr(fcntl, "ioctl", ioctl)

    dashboard = cast(tui.RPiDashboard, SimpleNamespace())
    result = tui.RPiDashboard.get_interfaces_info(dashboard)

    assert result == ("eth0: 192.0.2.20", None)


def test_hotspot_info_keeps_default_ssid_and_counts_dhcp_leases(monkeypatch) -> None:
    widgets: dict[str, Any] = {
        "#txt_hotspot_ssid": SimpleNamespace(update=lambda value: setattr(widgets["#txt_hotspot_ssid"], "text", value)),
        "#txt_hotspot_clients": SimpleNamespace(update=lambda value: setattr(widgets["#txt_hotspot_clients"], "text", value)),
        "#switch_hotspot": SimpleNamespace(value=False),
        "#switch_raspotify": SimpleNamespace(value=True),
    }
    files = {
        "/etc/hostapd/rpi-service.conf": "interface=wlan0\nssid=   \n",
        "/var/lib/misc/dnsmasq.leases": "lease-one\nlease-two\n",
    }

    def open_file(path: str, *_args, **_kwargs):
        if path not in files:
            raise FileNotFoundError(path)
        return io.StringIO(files[path])

    monkeypatch.setattr(tui, "open", open_file, raising=False)
    monkeypatch.setattr(
        tui.os.path,
        "lexists",
        lambda path: path == "/run/systemd/units/invocation:hostapd.service",
    )
    dashboard = cast(
        tui.RPiDashboard,
        SimpleNamespace(
            language="cz",
            query_one=lambda selector, _widget: widgets[selector],
            write_log=lambda _message: None,
        ),
    )

    asyncio.run(tui.RPiDashboard.update_wifi_hotspot_info(dashboard))

    assert widgets["#txt_hotspot_ssid"].text == "Hotspot SSID: [bold]RPi-service[/] (skryta)"
    assert widgets["#txt_hotspot_clients"].text == "Pripojeni klienti: [bold]2[/]"
    assert widgets["#switch_hotspot"].value is True
    assert widgets["#switch_raspotify"].value is False

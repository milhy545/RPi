"""Regresní testy čtení procesů z procfs v hardwarovém guardu."""

from __future__ import annotations

import io
from typing import Any
from unittest.mock import Mock, patch

from rpi_dashboard.ci import rpi_guard


def _stat_line(
    pid: int,
    comm: str,
    ppid: int,
    user_ticks: int,
    system_ticks: int,
    start_ticks: int,
) -> str:
    fields = ["0"] * 20
    fields[0] = "S"
    fields[1] = str(ppid)
    fields[11] = str(user_ticks)
    fields[12] = str(system_ticks)
    fields[19] = str(start_ticks)
    return f"{pid} ({comm}) {' '.join(fields)}"


def test_process_scan_reads_proc_stat_and_cmdline_without_ps(monkeypatch) -> None:
    stat_entries = {
        "/proc/101/stat": _stat_line(101, "player ) wrapper", 1, 20, 10, 1000),
        "/proc/202/stat": _stat_line(202, "mpv", 1, 0, 0, 0),
        "/proc/303/stat": "303 malformed process stat",
    }
    cmdline_entries = {
        "/proc/101/cmdline": b"/usr/bin/python3\0tui.py\0--flag\0",
        "/proc/202/cmdline": b"",
    }

    def open_proc(path: str, mode: str = "r", *_args: Any, **_kwargs: Any) -> Any:
        if path == "/proc/uptime":
            return io.StringIO("20.00 0.00\n")
        if path in stat_entries:
            return io.StringIO(stat_entries[path])
        if path in cmdline_entries and mode == "rb":
            return io.BytesIO(cmdline_entries[path])
        raise FileNotFoundError(path)

    monkeypatch.setattr(
        rpi_guard.os,
        "listdir",
        lambda path: ["101", "202", "303", "404", "self"],
    )
    monkeypatch.setattr(rpi_guard.os, "sysconf", lambda _name: 100)

    def unexpected_run(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("process discovery must not spawn ps")

    monkeypatch.setattr(rpi_guard.subprocess, "run", unexpected_run)
    with patch("builtins.open", side_effect=open_proc):
        processes = rpi_guard.RPiGuard()._get_processes()

    assert processes == [
        {
            "pid": 101,
            "ppid": 1,
            "pcpu": 3.0,
            "comm": "player ) wrapper",
            "args": "/usr/bin/python3 tui.py --flag",
        },
        {
            "pid": 202,
            "ppid": 1,
            "pcpu": 0.0,
            "comm": "mpv",
            "args": "[mpv]",
        },
    ]


def test_process_scan_returns_empty_if_uptime_is_unavailable(monkeypatch) -> None:
    mocked_listdir = Mock()
    monkeypatch.setattr(rpi_guard.os, "listdir", mocked_listdir)

    with patch("builtins.open", side_effect=OSError("procfs unavailable")):
        assert rpi_guard.RPiGuard()._get_processes() == []

    mocked_listdir.assert_not_called()


def test_process_scan_returns_empty_if_procfs_directory_is_unavailable(monkeypatch) -> None:
    def open_uptime(path: str, *_args: Any, **_kwargs: Any) -> Any:
        if path == "/proc/uptime":
            return io.StringIO("20.00 0.00\n")
        raise FileNotFoundError(path)

    mocked_listdir = Mock(side_effect=PermissionError("procfs unavailable"))
    monkeypatch.setattr(rpi_guard.os, "listdir", mocked_listdir)
    monkeypatch.setattr(rpi_guard.os, "sysconf", lambda _name: 100)

    with patch("builtins.open", side_effect=open_uptime):
        assert rpi_guard.RPiGuard()._get_processes() == []

    mocked_listdir.assert_called_once_with("/proc")


def test_process_scan_handles_invalid_entries_and_unreadable_cmdline(monkeypatch) -> None:
    valid_stat = _stat_line(405, "fresh process", 1, 10, 5, 2500)

    def open_proc(path: str, mode: str = "r", *_args: Any, **_kwargs: Any) -> Any:
        if path == "/proc/uptime":
            return io.StringIO("20.00 0.00\n")
        if path == "/proc/401/stat":
            return io.StringIO("401 malformed stat")
        if path == "/proc/402/stat":
            return io.StringIO("402 no opening parenthesis")
        if path == "/proc/403/stat":
            return io.StringIO("403 (short) S 1 2")
        if path == "/proc/404/stat":
            raise FileNotFoundError(path)
        if path == "/proc/405/stat":
            return io.StringIO(valid_stat)
        if path == "/proc/405/cmdline" and mode == "rb":
            raise PermissionError(path)
        raise AssertionError(f"Unexpected procfs read: {path} ({mode})")

    monkeypatch.setattr(
        rpi_guard.os,
        "listdir",
        lambda path: ["self", "401", "402", "403", "404", "405"],
    )
    monkeypatch.setattr(
        rpi_guard.os,
        "sysconf",
        Mock(side_effect=OSError("clock tick rate unavailable")),
    )

    with patch("builtins.open", side_effect=open_proc):
        processes = rpi_guard.RPiGuard()._get_processes()

    assert processes == [
        {
            "pid": 405,
            "ppid": 1,
            "pcpu": 0.0,
            "comm": "fresh process",
            "args": "[fresh process]",
        }
    ]


def test_process_scan_uses_default_clock_rate_when_sysconf_is_nonpositive(monkeypatch) -> None:
    stat_entry = _stat_line(501, "worker", 1, 10, 5, 100)

    def open_proc(path: str, mode: str = "r", *_args: Any, **_kwargs: Any) -> Any:
        if path == "/proc/uptime":
            return io.StringIO("20.00 0.00\n")
        if path == "/proc/501/stat":
            return io.StringIO(stat_entry)
        if path == "/proc/501/cmdline" and mode == "rb":
            return io.BytesIO(b"worker\0--safe\0")
        raise AssertionError(f"Unexpected procfs read: {path} ({mode})")

    monkeypatch.setattr(rpi_guard.os, "listdir", lambda _path: ["501"])
    monkeypatch.setattr(rpi_guard.os, "sysconf", lambda _name: 0)

    with patch("builtins.open", side_effect=open_proc):
        processes = rpi_guard.RPiGuard()._get_processes()

    assert processes == [
        {
            "pid": 501,
            "ppid": 1,
            "pcpu": 15.0 / 19.0,
            "comm": "worker",
            "args": "worker --safe",
        }
    ]

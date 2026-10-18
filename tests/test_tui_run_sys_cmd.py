"""Regresní testy spouštění příkazů v TUI."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, cast

import tui


class _FakeProcess:
    def __init__(
        self,
        returncode: int = 0,
        output: tuple[bytes, bytes] = (b"output\n", b""),
        communicate_error: Exception | None = None,
    ) -> None:
        self.returncode = returncode
        self.output = output
        self.communicate_error = communicate_error
        self.killed = False
        self.waited = False

    async def communicate(self) -> tuple[bytes, bytes]:
        if self.communicate_error is not None:
            raise self.communicate_error
        return self.output

    def kill(self) -> None:
        self.killed = True

    async def wait(self) -> int:
        self.waited = True
        return self.returncode


def _dashboard(log_messages: list[str] | None = None) -> tui.RPiDashboard:
    messages = log_messages if log_messages is not None else []
    return cast(tui.RPiDashboard, SimpleNamespace(write_log=messages.append))


def test_run_sys_cmd_uses_exec_and_preserves_arguments(monkeypatch) -> None:
    calls: list[tuple[tuple[str, ...], dict[str, Any]]] = []

    async def fake_exec(*args: str, **kwargs: Any) -> _FakeProcess:
        calls.append((args, kwargs))
        return _FakeProcess()

    async def unexpected_shell(*_args: Any, **_kwargs: Any) -> _FakeProcess:
        raise AssertionError("simple commands should not start a shell")

    monkeypatch.setattr(tui.asyncio, "create_subprocess_exec", fake_exec)
    monkeypatch.setattr(tui.asyncio, "create_subprocess_shell", unexpected_shell)

    result = asyncio.run(tui.RPiDashboard.run_sys_cmd(_dashboard(), "pactl list short sinks"))

    assert result == "output"
    assert calls[0][0] == ("pactl", "list", "short", "sinks")


def test_run_sys_cmd_keeps_shell_for_quoted_arguments_and_builtins(monkeypatch) -> None:
    commands: list[str] = []

    async def fake_shell(command: str, **_kwargs: Any) -> _FakeProcess:
        commands.append(command)
        return _FakeProcess()

    async def unexpected_exec(*_args: Any, **_kwargs: Any) -> _FakeProcess:
        raise AssertionError("shell syntax must not be split into argv")

    monkeypatch.setattr(tui.asyncio, "create_subprocess_shell", fake_shell)
    monkeypatch.setattr(tui.asyncio, "create_subprocess_exec", unexpected_exec)

    asyncio.run(
        tui.RPiDashboard.run_sys_cmd(_dashboard(), "nmcli dev wifi connect 'Living Room'")
    )
    asyncio.run(tui.RPiDashboard.run_sys_cmd(_dashboard(), "  cd /tmp"))

    assert commands == [
        "nmcli dev wifi connect 'Living Room'",
        "  cd /tmp",
    ]


def test_run_sys_cmd_returns_empty_for_blank_command(monkeypatch) -> None:
    async def unexpected_process(*_args: Any, **_kwargs: Any) -> _FakeProcess:
        raise AssertionError("blank commands should not start a process")

    monkeypatch.setattr(tui.asyncio, "create_subprocess_exec", unexpected_process)
    monkeypatch.setattr(tui.asyncio, "create_subprocess_shell", unexpected_process)

    result = asyncio.run(tui.RPiDashboard.run_sys_cmd(_dashboard(), "  \t"))

    assert result == ""


def test_run_sys_cmd_kills_and_waits_for_timed_out_process(monkeypatch) -> None:
    process = _FakeProcess(communicate_error=asyncio.TimeoutError())

    async def fake_exec(*_args: str, **_kwargs: Any) -> _FakeProcess:
        return process

    messages: list[str] = []
    monkeypatch.setattr(tui.asyncio, "create_subprocess_exec", fake_exec)

    result = asyncio.run(
        tui.RPiDashboard.run_sys_cmd(_dashboard(messages), "pactl info", timeout=0.01)
    )

    assert result == ""
    assert process.killed is True
    assert process.waited is True
    assert messages and messages[0].startswith("[TIMEOUT]")

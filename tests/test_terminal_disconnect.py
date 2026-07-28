from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from rpi_dashboard.services.terminal import terminal_ws_handler


class FakeWebSocket:
    def __init__(self, messages: list[str], disconnect_delay: float = 0.6) -> None:
        self.remote_address = ("127.0.0.1", 12345)
        self.request = SimpleNamespace(path="?token=secret")
        self._messages = iter(messages)
        self.disconnect_delay = disconnect_delay
        self.closed: list[tuple[int, str]] = []
        self.sent_payloads: list[str] = []

    def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        try:
            return next(self._messages)
        except StopIteration as exc:
            await asyncio.sleep(self.disconnect_delay)
            raise StopAsyncIteration from exc

    async def close(self, code: int, reason: str) -> None:
        self.closed.append((code, reason))

    async def send(self, payload: str) -> None:
        self.sent_payloads.append(payload)
        raise BrokenPipeError("client disconnected")


class DummyProcess:
    async def communicate(self) -> tuple[bytes, bytes]:
        return b"", b""


@pytest.mark.asyncio
async def test_terminal_ws_handler_survives_client_disconnect(monkeypatch: pytest.MonkeyPatch) -> None:
    websocket = FakeWebSocket(
        [
            json.dumps({"action": "attach", "session": "RPi", "cols": 80, "rows": 24}),
        ]
    )

    monkeypatch.setattr(
        "rpi_dashboard.services.terminal.asyncio.create_subprocess_exec",
        AsyncMock(return_value=DummyProcess()),
    )
    monkeypatch.setattr(
        "rpi_dashboard.services.terminal.subprocess.run",
        lambda *args, **kwargs: MagicMock(returncode=0, stdout="", stderr=""),
    )

    await terminal_ws_handler(websocket, "secret", lambda ip: True, session_name="RPi")

    assert websocket.closed == []
    assert websocket.sent_payloads

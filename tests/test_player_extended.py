"""Behavior tests for mpv IPC, pooling, and playback memory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rpi_dashboard.services import player


class FakeSocket:
    def __init__(self, response: bytes = b'{"data": true}\n', peek_error: Exception | None = None) -> None:
        self.response = response
        self.peek_error = peek_error
        self.sent: list[bytes] = []
        self.timeouts: list[float] = []
        self.closed = False

    def settimeout(self, value: float) -> None:
        self.timeouts.append(value)

    def connect(self, path: str) -> None:
        self.path = path

    def sendall(self, data: bytes) -> None:
        self.sent.append(data)

    def recv(self, _size: int, flags: int = 0) -> bytes:
        if flags and self.peek_error:
            raise self.peek_error
        return self.response

    def close(self) -> None:
        self.closed = True


def test_url_cache_persists_and_expires(tmp_path: Path, monkeypatch: Any) -> None:
    cache_file = tmp_path / "cache.json"
    monkeypatch.setattr(player.time, "time", lambda: 100.0)
    cache = player._URLCache(str(cache_file), ttl=10)
    cache.put("video", {"url": "stream"})
    assert cache.get("video") == {"url": "stream"}
    assert player._URLCache(str(cache_file), ttl=10).get("video") == {"url": "stream"}

    monkeypatch.setattr(player.time, "time", lambda: 111.0)
    assert cache.get("video") is None
    assert json.loads(cache_file.read_text()) == {}


def test_url_cache_ignores_invalid_files(tmp_path: Path) -> None:
    cache_file = tmp_path / "cache.json"
    cache_file.write_text("not-json")
    assert player._URLCache(str(cache_file))._data == {}


def test_socket_pool_reuses_live_socket_and_closes_overflow(monkeypatch: Any) -> None:
    pooled = FakeSocket(peek_error=BlockingIOError())
    pool = player._MPVSocketPool(max_size=1)
    pool._pool.append(pooled)
    assert pool.get() is pooled
    assert pool.stats() == {"available": 0, "in_use": 1, "max_size": 1}
    pool.put(pooled)

    overflow = FakeSocket()
    pool.put(overflow)
    assert overflow.closed is True
    pool.close_all()
    assert pooled.closed is True
    assert pool.stats()["available"] == 0


def test_socket_pool_discards_dead_socket(monkeypatch: Any) -> None:
    dead = FakeSocket(peek_error=OSError("closed"))
    fresh = FakeSocket()
    pool = player._MPVSocketPool()
    pool._pool.append(dead)
    monkeypatch.setattr(pool, "_create_socket", lambda: fresh)
    assert pool.get() is fresh
    assert dead.closed is True


def test_mpv_ipc_and_command_contract(monkeypatch: Any) -> None:
    sock = FakeSocket(b'{"data": 42}\n')
    monkeypatch.setattr(player._mpv_pool, "get", lambda: sock)
    monkeypatch.setattr(player._mpv_pool, "put", lambda value: None)
    assert player.mpv_ipc_socket_live() is True
    assert player.mcmd("get_property", "volume") == 42
    assert b'"method": "command"' in sock.sent[-1]

    monkeypatch.setattr(player._mpv_pool, "get", lambda: None)
    assert player.mpv_ipc_socket_live() is False
    assert player.mcmd("quit") is None


def test_mpv_start_stop_and_status(monkeypatch: Any) -> None:
    class Proc:
        pid = 4321

    commands: list[list[str]] = []

    def popen(command: list[str], **kwargs: Any) -> Proc:
        commands.append(command)
        return Proc()

    monkeypatch.setattr(player.subprocess, "Popen", popen)
    assert player.mpv_start("movie.mp4", quality="360p", resume=True) == {"ok": True, "pid": 4321}
    assert "--start=0" in commands[0]
    assert "--ytdl-format=" + player.QUALITY["360p"] in commands[0]

    calls: list[tuple[Any, ...]] = []
    monkeypatch.setattr(player, "mpv_ipc_socket_live", lambda: True)
    monkeypatch.setattr(player, "mcmd", lambda *args: calls.append(args))
    monkeypatch.setattr(player, "_run", lambda *args, **kwargs: object())
    monkeypatch.setattr(player.time, "sleep", lambda _: None)
    assert player.mpv_stop() == {"ok": True}
    assert calls == [("quit",)]

    values = {"time-pos": 12, "duration": 90, "paused": True, "filename": "movie.mp4", "volume": 55, "idle-active": False}
    monkeypatch.setattr(player, "mget", lambda key: values.get(key))
    status = player.mpv_st()
    assert status["ok"] is True
    assert status["title"] == "movie.mp4"
    assert status["vol"] == 55


def test_player_controls_and_failure_paths(monkeypatch: Any) -> None:
    writes: list[tuple[str, Any]] = []
    monkeypatch.setattr(player, "mget", lambda key: 145 if key == "volume" else False)
    monkeypatch.setattr(player, "mset", lambda key, value: writes.append((key, value)))
    assert player.mpv_volume_delta(20)["volume"] == 150
    assert player.mpv_pause() == {"ok": True, "paused": True}
    assert player.mpv_seek_absolute(7.5) == {"ok": True}
    assert writes == [("volume", 150), ("paused", True)]

    def fail(*args: Any, **kwargs: Any) -> None:
        raise OSError("ipc failed")

    monkeypatch.setattr(player, "mset", fail)
    assert player.mpv_seek(1)["ok"] is False
    assert player.mpv_volume(10)["ok"] is False


def test_playback_memory_lifecycle(tmp_path: Path, monkeypatch: Any) -> None:
    memory_file = tmp_path / "playback-memory.json"
    monkeypatch.setattr(player, "_playback_memory_file", lambda: str(memory_file))
    monkeypatch.setattr(player, "mpv_ipc_socket_live", lambda: True)
    monkeypatch.setattr(player.time, "time", lambda: 123.0)
    source_url = "https://youtu.be/dQw4w9WgXcQ"
    values: dict[str, Any] = {"time-pos": 40, "duration": 100, "media-title": "Demo", "path": source_url}
    monkeypatch.setattr(player, "mget", lambda key: values[key])

    saved = player.save_mpv_resume_memory()
    assert saved == {"position": 40.0, "duration": 100.0, "title": "Demo", "timestamp": 123.0}
    assert player.mpv_memory_for_url(source_url) == saved
    assert player.mpv_memory_clear_for_url(source_url) is True
    assert player.mpv_memory_clear_for_url(source_url) is False


def test_playback_memory_skips_start_and_clears_near_end(tmp_path: Path, monkeypatch: Any) -> None:
    memory_file = tmp_path / "playback-memory.json"
    monkeypatch.setattr(player, "_playback_memory_file", lambda: str(memory_file))
    monkeypatch.setattr(player, "mpv_ipc_socket_live", lambda: True)
    values = {"time-pos": 3, "duration": 100, "media-title": "Demo", "path": "movie.mp4"}
    monkeypatch.setattr(player, "mget", lambda key: values[key])
    assert player.save_mpv_resume_memory() is None

    player._save_playback_memory({player._playback_media_key("movie.mp4"): {"position": 20}})
    values["time-pos"] = 96
    assert player.save_mpv_resume_memory() is None
    assert player.mpv_memory_for_url("movie.mp4") is None


def test_eof_detection_listener_and_auto_return(monkeypatch: Any) -> None:
    monkeypatch.setattr(player, "mpv_ipc_socket_live", lambda: True)
    monkeypatch.setattr(player, "mget", lambda key: key == "eof-reached")
    assert player.mpv_ended() is True

    callbacks: list[str] = []

    class ImmediateThread:
        def __init__(self, target: Any, daemon: bool) -> None:
            self.target = target

        def start(self) -> None:
            self.target()

    monkeypatch.setattr("threading.Thread", ImmediateThread)
    monkeypatch.setattr(player.time, "sleep", lambda _: None)
    assert player.mpv_listen_for_eof(lambda: callbacks.append("eof")) is True
    assert callbacks == ["eof"]

    captured: list[Any] = []

    def capture_listener(callback: Any = None, **kwargs: Any) -> bool:
        captured.append(callback)
        return True

    monkeypatch.setattr(player, "mpv_listen_for_eof", capture_listener)
    monkeypatch.setattr(player, "save_mpv_resume_memory", lambda: None)
    returned: list[tuple[str, str]] = []
    monkeypatch.setattr(player.return_service, "return_to_dashboard", lambda reason, source: returned.append((reason, source)))
    assert player.mpv_auto_return_on_eof() == {"ok": True}
    captured[0]()
    assert returned == [("eof", "mpv_eof")]


def test_cleanup_stale_socket(tmp_path: Path, monkeypatch: Any) -> None:
    socket_file = tmp_path / "mpv.sock"
    socket_file.write_text("stale")
    monkeypatch.setattr(player, "MSOCK", str(socket_file))
    player.cleanup_stale_mpv_socket()
    assert not socket_file.exists()

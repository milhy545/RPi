"""Behavior tests for media URL resolution and cookie diagnostics."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from rpi_dashboard.services import media


class FakeYoutubeDL:
    info: dict[str, Any] = {}
    options: dict[str, Any] = {}

    def __init__(self, options: dict[str, Any]) -> None:
        type(self).options = options

    def __enter__(self) -> "FakeYoutubeDL":
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def extract_info(self, url: str, download: bool) -> dict[str, Any]:
        self.url = url
        return type(self).info


def install_fake_ytdlp(monkeypatch: Any, info: dict[str, Any]) -> None:
    FakeYoutubeDL.info = info
    monkeypatch.setitem(sys.modules, "yt_dlp", SimpleNamespace(YoutubeDL=FakeYoutubeDL))


def test_norm_and_direct_resolution() -> None:
    assert media.norm(" https://example.com/a//b/../c?q=1 ") == "https://example.com/a/c?q=1"
    assert media.norm(cast(Any, None)) == ""
    assert media.resolve("https://example.com/video.mp4") == (
        "https://example.com/video.mp4",
        {"title": "https://example.com/video.mp4"},
    )


def test_youtube_resolution_uses_direct_stream_and_cookie(monkeypatch: Any, tmp_path: Path) -> None:
    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text("cookie")
    monkeypatch.setattr(media, "_cookies_path", lambda: str(cookie_file))
    install_fake_ytdlp(monkeypatch, {"url": "https://cdn/stream", "title": "Demo", "height": 720, "duration": 12})
    stream, metadata = media.resolve("https://youtu.be/dQw4w9WgXcQ", "720p")
    assert stream == "https://cdn/stream"
    assert metadata == {"id": "dQw4w9WgXcQ", "title": "Demo", "h": 720, "dur": 12}
    assert FakeYoutubeDL.options["cookiefile"] == str(cookie_file)


def test_youtube_resolution_selects_highest_muxed_format(monkeypatch: Any) -> None:
    install_fake_ytdlp(monkeypatch, {
        "formats": [
            {"url": "audio", "height": None, "vcodec": "none", "acodec": "aac"},
            {"url": "low", "height": 360, "vcodec": "h264", "acodec": "aac"},
            {"url": "high", "height": 1080, "vcodec": "h264", "acodec": "aac"},
        ]
    })
    assert media.resolve("https://youtu.be/dQw4w9WgXcQ")[0] == "high"

    install_fake_ytdlp(monkeypatch, {"formats": []})
    with pytest.raises(RuntimeError, match="No playable URL"):
        media.resolve("https://youtu.be/dQw4w9WgXcQ")


def test_cookie_status_reports_auth_and_age(monkeypatch: Any, tmp_path: Path) -> None:
    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text("# Netscape\n.youtube.com\tTRUE\t/\tTRUE\t0\tSID\tsecret\n")
    os.utime(cookie_file, (100, 100))
    monkeypatch.setattr(media, "_cookies_path", lambda: str(cookie_file))
    monkeypatch.setattr("time.time", lambda: 150.0)
    status = media.youtube_cookie_status()
    assert status["ok"] is True
    assert status["cookie_count"] == 1
    assert status["age_seconds"] == 50
    assert status["has_auth_cookies"] is True
    assert status["recommendation"] == "OK"


def test_cookie_status_when_missing(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(media, "_cookies_path", lambda: str(tmp_path / "missing.txt"))
    status = media.youtube_cookie_status()
    assert status["exists"] is False
    assert status["ok"] is False


def test_youtube_age_check_success_and_failure(monkeypatch: Any) -> None:
    assert media.youtube_age_check("") == {"ok": False, "error": "url required"}
    monkeypatch.setattr(media, "resolve", lambda url, quality: ("stream", {"title": "Demo", "id": "id", "dur": 10, "h": 720}))
    monkeypatch.setattr(media, "youtube_cookie_status", lambda: {"ok": True})
    result = media.youtube_age_check("url")
    assert result["ok"] is True
    assert result["playable_url"] is True

    def fail(url: str, quality: str) -> None:
        raise RuntimeError("blocked")

    monkeypatch.setattr(media, "resolve", fail)
    assert media.youtube_age_check("url")["error"] == "blocked"


def test_media_preview_direct_and_youtube(monkeypatch: Any) -> None:
    assert media.media_preview("") == {"ok": False, "error": "url required"}
    direct = media.media_preview("https://example.com/path/movie.mp4")
    assert direct["type"] == "direct"
    assert direct["title"] == "movie.mp4"

    install_fake_ytdlp(monkeypatch, {"title": "Demo", "duration": 20, "uploader": "Owner", "thumbnails": [{"url": "thumb"}]})
    preview = media.media_preview("https://youtu.be/dQw4w9WgXcQ")
    assert preview["ok"] is True
    assert preview["thumbnail"] == "thumb"
    assert preview["uploader"] == "Owner"


def test_media_preview_youtube_failure(monkeypatch: Any) -> None:
    class FailingYoutubeDL(FakeYoutubeDL):
        def extract_info(self, url: str, download: bool) -> dict[str, Any]:
            raise RuntimeError("network unavailable")

    monkeypatch.setitem(sys.modules, "yt_dlp", SimpleNamespace(YoutubeDL=FailingYoutubeDL))
    result = media.media_preview("https://youtu.be/dQw4w9WgXcQ")
    assert result["ok"] is False
    assert result["thumbnail"].endswith("/dQw4w9WgXcQ/hqdefault.jpg")

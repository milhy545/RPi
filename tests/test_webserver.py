import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from webserver import norm, yt_id

@pytest.mark.parametrize("input_url, expected", [
    # Happy paths: normalizer removes redundant slashes in path
    ("http://example.com//test//path", "http://example.com/test/path"),
    ("https://example.com/test///path//", "https://example.com/test/path/"),
    ("http://example.com", "http://example.com"),
    ("https://example.com/normal/path", "https://example.com/normal/path"),

    # URL with query and fragment
    ("http://example.com//path?query=1#frag", "http://example.com/path?query=1#frag"),

    # Strip spaces
    ("  http://example.com//test  ", "http://example.com/test"),

    # Non HTTP/HTTPS schemes (should strip but NOT normalize slashes)
    ("ftp://example.com//test//path", "ftp://example.com//test//path"),
    ("file:///home//user//test", "file:///home//user//test"),

    # Malformed strings (should fallback to returning stripped string)
    ("just a random string", "just a random string"),
    ("http://[invalid-ipv6]//path", "http://[invalid-ipv6]//path"),

    # Non-string inputs (should safely return empty string)
    (None, ""),
    (123, ""),
    (3.14, ""),
    (["http://example.com"], ""),
    ({"url": "http://example.com"}, "")
])
def test_norm(input_url, expected):
    """Test the norm function for URL normalization and type safety."""
    assert norm(input_url) == expected

def test_yt_id_standard_url():
    assert yt_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert yt_id("http://youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

def test_yt_id_short_url():
    assert yt_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert yt_id("http://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

def test_yt_id_shorts_url():
    assert yt_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

def test_yt_id_embed_url():
    assert yt_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

def test_yt_id_with_extra_params():
    assert yt_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s") == "dQw4w9WgXcQ"
    assert yt_id("https://www.youtube.com/watch?feature=youtu.be&v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

def test_yt_id_invalid_urls():
    assert yt_id("https://www.google.com") == ""
    assert yt_id("not a url at all") == ""
    assert yt_id("https://youtube.com/watch?v=") == ""  # Too short ID, won't match regex exactly
    assert yt_id("") == ""

def test_yt_id_with_whitespace():
    # `norm` is used inside `yt_id`, which does `u.strip()`
    assert yt_id("  https://youtu.be/dQw4w9WgXcQ  ") == "dQw4w9WgXcQ"


def test_mpv_start_uses_resolved_stream_without_embedded_ytdl(monkeypatch, tmp_path):
    """A YouTube request must play the freshly resolved URL, not re-resolve it in mpv."""
    import webserver

    commands = []

    class Proc:
        pid = 1234

        def poll(self):
            return None

    def popen(command, **kwargs):
        commands.append(command)
        return Proc()

    stream_url = "https://media.example.test/fresh.mp4"
    monkeypatch.setattr(
        webserver,
        "resolve",
        lambda url, quality: (stream_url, {"title": "Fresh", "h": 720, "audio_url": "https://media.example.test/audio.m4a"}),
    )
    monkeypatch.setattr(webserver, "mpv_stop", lambda: {"ok": True})
    monkeypatch.setattr(webserver.subprocess, "Popen", popen)
    monkeypatch.setattr(webserver.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setattr(webserver.time, "sleep", lambda _: None)
    monkeypatch.setattr(webserver, "_mpv_video_ready", lambda: True)
    monkeypatch.setattr(webserver, "MPV_LOG", str(tmp_path / "mpv.log"))

    result = webserver.mpv_start("https://youtu.be/dQw4w9WgXcQ", "720p")

    assert result["ok"] is True
    assert commands[0][-1] == stream_url
    assert "--ytdl=no" in commands[0]
    assert "--ytdl=yes" not in commands[0]
    assert "--drm-mode=1280x720" in commands[0]
    assert "--video-unscaled=yes" in commands[0]
    assert "--keep-open=always" not in commands[0]
    assert "--hwdec=auto" in commands[0]
    assert "--scale=bilinear" not in commands[0]
    assert "--cscale=bilinear" not in commands[0]
    assert "--ao=alsa" in commands[0]
    assert "--audio-device=alsa/hdmi:CARD=vc4hdmi,DEV=0" in commands[0]
    assert "--ao=pulse" not in commands[0]
    assert "--vo=drm" in commands[0]
    assert "--gpu-context=drm" not in commands[0]
    assert "--audio-file=https://media.example.test/audio.m4a" in commands[0]


def test_quality_options_are_real_select_options():
    import webserver

    html = webserver.quality_options_html()

    assert '{{QUALITY_OPTIONS}}' not in html
    assert '<option value="720p" selected>720p</option>' in html


def test_resolve_uses_selected_video_and_audio_streams(monkeypatch):
    import webserver

    class Downloader:
        def __init__(self, options):
            assert "bv*[vcodec^=avc1]" in options["format"]
            assert "+ba[ext=m4a]" in options["format"]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def extract_info(self, url, download):
            return {
                "title": "720 test",
                "requested_formats": [
                    {"url": "https://media.example.test/video.mp4", "vcodec": "avc1", "acodec": "none", "height": 720},
                    {"url": "https://media.example.test/audio.m4a", "vcodec": "none", "acodec": "mp4a"},
                ],
            }

    monkeypatch.setattr("yt_dlp.YoutubeDL", Downloader)
    stream_url, meta = webserver.resolve("https://youtu.be/dQw4w9WgXcQ", "720p")

    assert stream_url == "https://media.example.test/video.mp4"
    assert meta["audio_url"] == "https://media.example.test/audio.m4a"
    assert meta["h"] == 720


def test_mpv_start_rejects_process_without_video_initialisation(monkeypatch, tmp_path):
    """A live MPV process is insufficient when no video stream becomes available."""
    import webserver

    class Proc:
        pid = 1234

        def poll(self):
            return None

    monotonic_values = iter((0.0, 7.0))
    monkeypatch.setattr(webserver, "resolve", lambda url, quality: (url, {"title": "Broken"}))
    monkeypatch.setattr(webserver, "mpv_stop", lambda: {"ok": True})
    monkeypatch.setattr(webserver.subprocess, "Popen", lambda *args, **kwargs: Proc())
    monkeypatch.setattr(webserver.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setattr(webserver.time, "sleep", lambda _: None)
    monkeypatch.setattr(webserver.time, "monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr(webserver, "_mpv_video_ready", lambda: False)
    monkeypatch.setattr(webserver, "MPV_READY_TIMEOUT", 6.0)
    monkeypatch.setattr(webserver, "MPV_LOG", str(tmp_path / "mpv.log"))

    result = webserver.mpv_start("https://example.test/broken.mp4")

    assert result["ok"] is False
    assert "did not initialise video" in result["error"]


def test_mpv_start_tolerates_audio_profile_timeout(monkeypatch, tmp_path):
    """Audio-route setup must not prevent otherwise working video playback."""
    import subprocess
    import webserver

    class Proc:
        pid = 1234

        def poll(self):
            return None

    def timed_out_audio_route(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(webserver, "resolve", lambda url, quality: (url, {"title": "Video"}))
    monkeypatch.setattr(webserver, "mpv_stop", lambda: {"ok": True})
    monkeypatch.setattr(webserver.subprocess, "run", timed_out_audio_route)
    monkeypatch.setattr(webserver.subprocess, "Popen", lambda *args, **kwargs: Proc())
    monkeypatch.setattr(webserver, "_mpv_video_ready", lambda: True)
    monkeypatch.setattr(webserver, "MPV_LOG", str(tmp_path / "mpv.log"))

    assert webserver.mpv_start("https://example.test/video.mp4")["ok"] is True


def test_mpv_video_ready_uses_its_own_ipc_request(monkeypatch):
    """Startup readiness must not depend on the reusable control-socket pool."""
    import webserver

    class Socket:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def settimeout(self, value):
            pass

        def connect(self, path):
            assert path == webserver.MSOCK

        def sendall(self, data):
            assert b'"video-params"' in data
            assert b'"request_id": 921' in data

        def recv(self, size):
            return b'{"request_id":921,"data":{"w":1920},"error":"success"}\n'

    monkeypatch.setattr(webserver.socket, "socket", lambda *args: Socket())
    assert webserver._mpv_video_ready() is True

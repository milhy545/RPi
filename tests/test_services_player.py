"""Tests for player service module."""

from unittest.mock import patch, MagicMock


def test_yt_id_standard():
    """Test YouTube ID extraction from standard URL."""
    from rpi_dashboard.services.player import yt_id
    assert yt_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_yt_id_short():
    """Test YouTube ID extraction from short URL."""
    from rpi_dashboard.services.player import yt_id
    assert yt_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_yt_id_shorts():
    """Test YouTube ID extraction from shorts URL."""
    from rpi_dashboard.services.player import yt_id
    assert yt_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_yt_id_invalid():
    """Test YouTube ID extraction from invalid URL."""
    from rpi_dashboard.services.player import yt_id
    assert yt_id("https://example.com") is None
    assert yt_id("") is None
    assert yt_id(None) is None


def test_mpv_start():
    """Test mpv start command."""
    from rpi_dashboard.services.player import mpv_start
    with patch("subprocess.Popen") as mock_popen:
        mock_popen.return_value = MagicMock(pid=12345)
        result = mpv_start("https://example.com/video.mp4")
        assert result["ok"] is True
        assert "pid" in result


def test_mpv_stop():
    """Test mpv stop command."""
    from rpi_dashboard.services.player import mpv_stop
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = mpv_stop()
        assert result["ok"] is True


def test_mpv_st_not_running():
    """Test mpv status when not running."""
    from rpi_dashboard.services.player import mpv_st
    with patch("rpi_dashboard.services.player.mpv_ipc_socket_live", return_value=False):
        result = mpv_st()
        assert result["on"] is False


def test_mpv_seek():
    """Test mpv seek command."""
    from rpi_dashboard.services.player import mpv_seek
    with patch("rpi_dashboard.services.player.mset") as mock_mset:
        result = mpv_seek(60.0)
        assert result["ok"] is True
        mock_mset.assert_called_once_with("time-pos", 60.0)


def test_mpv_volume():
    """Test mpv volume command."""
    from rpi_dashboard.services.player import mpv_volume
    with patch("rpi_dashboard.services.player.mset") as mock_mset:
        result = mpv_volume(50)
        assert result["ok"] is True
        assert result["volume"] == 50


def test_mpv_volume_clamp():
    """Test mpv volume clamping."""
    from rpi_dashboard.services.player import mpv_volume
    with patch("rpi_dashboard.services.player.mset") as mock_mset:
        result = mpv_volume(200)
        assert result["volume"] == 150  # Clamped
        
        result = mpv_volume(-10)
        assert result["volume"] == 0  # Clamped


def test_mpv_auto_return_on_eof():
    """Test mpv auto-return on EOF setup."""
    from rpi_dashboard.services.player import mpv_auto_return_on_eof
    with patch("rpi_dashboard.services.player.mpv_listen_for_eof", return_value=True):
        result = mpv_auto_return_on_eof()
        assert result["ok"] is True

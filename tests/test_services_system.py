"""Tests for system service module."""

from unittest.mock import patch, MagicMock


def test_get_cpu_usage():
    """Test CPU usage reading."""
    from rpi_dashboard.services.system import get_cpu_usage
    with patch("builtins.open", create=True) as mock_open:
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        mock_open.return_value.readline.return_value = "cpu  12345 678 9012 345678 901 234 567 0 0 0"
        result = get_cpu_usage()
        assert 0 <= result <= 100


def test_get_ram_usage():
    """Test RAM usage reading."""
    from rpi_dashboard.services.system import get_ram_usage
    with patch("builtins.open", create=True) as mock_open:
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        mock_open.return_value.__iter__ = lambda s: iter([
            "MemTotal:        1024000 kB\n",
            "MemAvailable:     512000 kB\n"
        ])
        result = get_ram_usage()
        assert "used_mb" in result
        assert "total_mb" in result
        assert "percent" in result


def test_get_cpu_temp():
    """Test CPU temperature reading."""
    from rpi_dashboard.services.system import get_cpu_temp
    with patch("builtins.open", create=True) as mock_open:
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        mock_open.return_value.read.return_value = "45000"
        result = get_cpu_temp()
        assert result == 45.0


def test_get_uptime():
    """Test uptime reading."""
    from rpi_dashboard.services.system import get_uptime
    with patch("builtins.open", create=True) as mock_open:
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        mock_open.return_value.readline.return_value = "86400.00 172800.00"
        result = get_uptime()
        assert "1d" in result


def test_get_system_stats():
    """Test system stats collection."""
    from rpi_dashboard.services.system import get_system_stats
    with patch("rpi_dashboard.services.system.get_cpu_usage", return_value=50.0):
        with patch("rpi_dashboard.services.system.get_cpu_temp", return_value=45.0):
            with patch("rpi_dashboard.services.system.get_ram_usage", return_value={"used_mb": 512, "total_mb": 1024, "percent": 50}):
                with patch("rpi_dashboard.services.system.get_disk_usage", return_value={"total": "32G", "used": "16G", "available": "16G", "percent": "50%"}):
                    with patch("rpi_dashboard.services.system.get_uptime", return_value="1d 0h"):
                        result = get_system_stats()
                        assert result["cpu_percent"] == 50.0
                        assert result["cpu_temp"] == 45.0


def test_restart_mpv():
    """Test mpv restart."""
    from rpi_dashboard.services.system import restart_mpv
    with patch("rpi_dashboard.services.system._run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = restart_mpv()
        assert result["ok"] is True


def test_restart_dashboard():
    """Test dashboard restart."""
    from rpi_dashboard.services.system import restart_dashboard
    with patch("rpi_dashboard.services.system._run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = restart_dashboard()
        assert result["ok"] is True


def test_get_network_info():
    """Test network info collection."""
    from rpi_dashboard.services.system import get_network_info
    with patch("rpi_dashboard.services.system._run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="192.168.0.100\n"
        )
        result = get_network_info()
        assert "ips" in result


def test_get_service_status():
    """Test service status check."""
    from rpi_dashboard.services.system import get_service_status
    with patch("rpi_dashboard.services.system._run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="active")
        result = get_service_status("rpi-dashboard")
        assert result["active"] is True
        assert result["status"] == "active"

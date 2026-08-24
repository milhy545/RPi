"""Tests for system service module."""

import subprocess
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


def test_dashboard_hostnames_and_ips_tolerate_tailscale_failures():
    """Network discovery should tolerate transient Tailscale outages."""
    from rpi_dashboard.services.system import dashboard_hostnames_and_ips

    with patch("rpi_dashboard.services.system.socket.gethostname", return_value="rpi-tv"):
        with patch("rpi_dashboard.services.system.subprocess.check_output", return_value="192.168.0.100\n"):
            with patch(
                "rpi_dashboard.services.system.subprocess.run",
                side_effect=[
                    MagicMock(returncode=1, stdout="", stderr=""),
                    MagicMock(returncode=1, stdout="", stderr=""),
                    MagicMock(returncode=1, stdout="", stderr=""),
                ],
            ):
                names, ips = dashboard_hostnames_and_ips()

    assert "rpi-tv" in names
    assert "127.0.0.1" in ips
    assert "192.168.0.100" in ips


def test_get_tailscale_status_handles_errors():
    """Tailscale status should degrade cleanly on failures."""
    from rpi_dashboard.services.system import get_tailscale_status

    with patch("rpi_dashboard.services.system._run", return_value=MagicMock(returncode=1, stdout="", stderr="timeout")):
        result = get_tailscale_status()

    assert result["connected"] is False


def test_get_service_status():
    """Test service status check."""
    from rpi_dashboard.services.system import get_service_status
    with patch("rpi_dashboard.services.system._run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="active")
        result = get_service_status("rpi-dashboard")
        assert result["active"] is True
        assert result["status"] == "active"


def test_get_system_status_tolerates_all_command_failures():
    """A missing systemctl or inactive unit must not raise HTTP 500."""
    from rpi_dashboard.services.system import get_system_status

    with patch(
        "rpi_dashboard.services.system._get_pid_by_name", return_value=""
    ), patch(
        "rpi_dashboard.services.system._run",
        side_effect=FileNotFoundError("systemctl not found"),
    ):
        result = get_system_status()

    for key in ("mpv", "dashboard", "keys2mpv", "webserver", "pipewire", "wireplumber"):
        entry = result[key]
        assert entry["pid"] == "", f"{key} pid should be empty on failure"
        assert entry["mask"] == "N/A", f"{key} mask should be N/A on failure"
    assert "summary" in result


def test_get_system_status_partial_failure():
    """Some services succeed, others fail -- the response must still be complete."""
    from rpi_dashboard.services.system import get_system_status

    # Simulate: mpv not running, dashboard alive, rest fail
    def _run_side_effect(cmd, t=5):
        unit = cmd[cmd.index("show") + 1] if "show" in cmd else ""
        if unit == "dashboard@milhy777":
            return MagicMock(returncode=0, stdout="1234")
        # Every other systemctl call fails
        raise FileNotFoundError("no such binary")

    with patch(
        "rpi_dashboard.services.system._get_pid_by_name", return_value=""
    ), patch("rpi_dashboard.services.system._run", side_effect=_run_side_effect):
        result = get_system_status()

    assert result["mpv"]["pid"] == ""
    assert result["dashboard"]["pid"] == "1234"
    assert result["keys2mpv"]["pid"] == ""
    assert result["webserver"]["pid"] == ""
    assert result["pipewire"]["pid"] == ""
    assert result["wireplumber"]["pid"] == ""


def test_unit_main_pid_user_flag_command_shape():
    """The helper must pass --user for user units and omit it for system units."""
    from rpi_dashboard.services.system import _unit_main_pid

    calls = []

    def _capture(cmd, t=5):
        calls.append(cmd)
        return MagicMock(returncode=0, stdout="99")

    with patch("rpi_dashboard.services.system._run", side_effect=_capture):
        pid_sys = _unit_main_pid("dashboard@milhy777")
        pid_user = _unit_main_pid("pipewire", user=True)

    assert pid_sys == "99"
    assert pid_user == "99"
    assert calls[0] == ["systemctl", "show", "dashboard@milhy777", "-p", "MainPID", "--value"]
    assert calls[1] == ["systemctl", "--user", "show", "pipewire", "-p", "MainPID", "--value"]


def test_unit_main_pid_handles_expected_command_failures():
    """Non-zero commands and timeouts should produce an empty PID."""
    from rpi_dashboard.services.system import _unit_main_pid

    with patch(
        "rpi_dashboard.services.system._run",
        return_value=MagicMock(returncode=1, stdout="", stderr="unit missing"),
    ):
        assert _unit_main_pid("missing") == ""

    with patch(
        "rpi_dashboard.services.system._run",
        side_effect=subprocess.TimeoutExpired(["systemctl"], timeout=5),
    ):
        assert _unit_main_pid("slow") == ""

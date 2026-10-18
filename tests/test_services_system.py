"""Tests for system service module."""

import io
import socket
import ctypes
import ipaddress
import subprocess
from unittest.mock import MagicMock, mock_open, patch


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
    """Signal every dashboard-owned mpv process and report their PIDs."""
    import signal

    from rpi_dashboard.services.system import restart_mpv

    with patch(
        "rpi_dashboard.services.system._get_dashboard_mpv_pids",
        return_value=[1234, 5678],
    ):
        with patch("rpi_dashboard.services.system.os.kill") as mock_kill:
            with patch("rpi_dashboard.services.system._run") as mock_run:
                result = restart_mpv()

    mock_run.assert_not_called()
    assert [invocation.args for invocation in mock_kill.call_args_list] == [
        (1234, signal.SIGTERM),
        (5678, signal.SIGTERM),
    ]
    assert result["ok"] is True
    assert result["signalled_pids"] == [1234, 5678]


def test_restart_mpv_does_not_signal_when_process_is_absent():
    """Chybějící proces nesmí způsobit signál jinému procesu."""
    from rpi_dashboard.services.system import restart_mpv

    with patch("rpi_dashboard.services.system._get_dashboard_mpv_pids", return_value=[]):
        with patch("rpi_dashboard.services.system.os.kill") as mock_kill:
            result = restart_mpv()

    mock_kill.assert_not_called()
    assert result == {"ok": False, "error": "mpv process not found"}


def test_restart_mpv_reports_signal_failures():
    """Vrátí chybu systému při selhání signálu."""
    from rpi_dashboard.services.system import restart_mpv

    with patch("rpi_dashboard.services.system._get_dashboard_mpv_pids", return_value=[1234]):
        with patch("rpi_dashboard.services.system.os.kill", side_effect=PermissionError("denied")):
            result = restart_mpv()

    assert result == {"ok": False, "error": "1234: denied", "signalled_pids": []}


def test_get_dashboard_mpv_pids_requires_exact_process_and_socket_match():
    """Ignore unrelated mpv processes and keep every dashboard IPC match."""
    from rpi_dashboard.services.system import _get_dashboard_mpv_pids

    process_data = {
        "/proc/101/comm": "mpv\n",
        "/proc/101/cmdline": b"mpv\0--input-ipc-server=/tmp/rpi-mpv.sock\0",
        "/proc/102/comm": "mpv\n",
        "/proc/102/cmdline": b"mpv\0--input-ipc-server=/tmp/other.sock\0",
        "/proc/103/comm": "mpv-wrapper\n",
        "/proc/103/cmdline": b"mpv-wrapper\0--input-ipc-server=/tmp/rpi-mpv.sock\0",
        "/proc/104/comm": "mpv\n",
        "/proc/104/cmdline": b"mpv\0--input-ipc-server\0/tmp/rpi-mpv.sock\0",
        "/proc/105/comm": "mpv\n",
        "/proc/105/cmdline": b"mpv\0--input-ipc-server=/tmp/mpv-socket\0",
        "/proc/106/comm": "mpv\n",
        "/proc/106/cmdline": b"mpv\0--input-ipc-server\0/tmp/mpv-socket\0",
    }

    def open_process_file(path: str, mode: str = "r", *_args, **_kwargs):
        contents = process_data[path]
        return io.BytesIO(contents) if mode == "rb" else io.StringIO(contents)

    with patch("rpi_dashboard.services.system.os.listdir", return_value=["106", "105", "104", "103", "102", "101"]):
        with patch("builtins.open", side_effect=open_process_file):
            assert _get_dashboard_mpv_pids() == [101, 104, 105, 106]


def test_get_pid_by_name_uses_exact_comm_match():
    """Za MPV nepovažuje wrappery ani příkazové řádky obsahující mpv."""
    from rpi_dashboard.services.system import _get_pid_by_name

    def open_comm(path, *_args, **_kwargs):
        names = {"/proc/101/comm": "mpv-wrapper\n", "/proc/102/comm": "mpv\n"}
        if path not in names:
            raise FileNotFoundError(path)
        return io.StringIO(names[path])

    with patch("rpi_dashboard.services.system.os.listdir", return_value=["101", "102"]):
        with patch("builtins.open", side_effect=open_comm):
            result = _get_pid_by_name("mpv")

    assert result == "102"


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
    with patch("rpi_dashboard.services.system._get_interface_addresses_native", return_value=["192.168.0.100"]):
        with patch("rpi_dashboard.services.system._get_default_gateway_native", return_value="192.168.0.1"):
            result = get_network_info()

    assert result == {"ips": ["192.168.0.100"], "gateway": "192.168.0.1"}


def test_get_network_info_falls_back_to_host_commands():
    """Use the command fallbacks when native network discovery is unavailable."""
    from rpi_dashboard.services.system import get_network_info

    with patch("rpi_dashboard.services.system._get_interface_addresses_native", return_value=[]):
        with patch("rpi_dashboard.services.system._get_default_gateway_native", return_value=None):
            with patch(
                "rpi_dashboard.services.system._run",
                side_effect=[
                    MagicMock(returncode=0, stdout="192.168.0.100 100.64.0.2\n"),
                    MagicMock(returncode=0, stdout="default via 192.168.0.1 dev eth0\n"),
                ],
            ) as mock_run:
                result = get_network_info()

    assert result == {"ips": ["192.168.0.100", "100.64.0.2"], "gateway": "192.168.0.1"}
    assert [call.args[0] for call in mock_run.call_args_list] == [
        ["hostname", "-I"],
        ["ip", "route", "show", "default"],
    ]


def test_native_interface_discovery_collects_ipv4_and_ipv6():
    """Read every usable interface address without spawning a subprocess."""
    from rpi_dashboard.services import system

    keepalive = []
    entries = []
    test_addresses = [
        ("lo", 0x9, "127.0.0.1"),
        ("eth0", 0x1, "192.168.0.100"),
        ("eth0", 0x1, "192.168.0.101"),
        ("tailscale0", 0x1, "100.64.0.2"),
        ("wlan0", 0x0, "192.168.0.9"),
        ("eth0", 0x1, "2001:db8::1"),
        ("eth0", 0x1, "fe80::1234"),
    ]
    for name, flags, raw_address in test_addresses:
        entry = system._IfAddrs()
        entry.ifa_name = name.encode("ascii")
        entry.ifa_flags = flags
        if ":" in raw_address:
            sockaddr = system._SockAddrIn6()
            sockaddr.sin6_family = socket.AF_INET6
            sockaddr.sin6_addr[:] = ipaddress.IPv6Address(raw_address).packed
        else:
            sockaddr = system._SockAddrIn()
            sockaddr.sin_family = socket.AF_INET
            sockaddr.sin_addr[:] = ipaddress.IPv4Address(raw_address).packed
        entry.ifa_addr = ctypes.cast(
            ctypes.pointer(sockaddr), ctypes.POINTER(system._SockAddr)
        )
        entries.append(entry)
        keepalive.append(sockaddr)

    for current, following in zip(entries, entries[1:]):
        current.ifa_next = ctypes.pointer(following)

    libc = MagicMock()

    def populate_interface_list(output_pointer):
        output = ctypes.cast(
            output_pointer, ctypes.POINTER(ctypes.POINTER(system._IfAddrs))
        )
        output[0] = ctypes.pointer(entries[0])
        return 0

    libc.getifaddrs.side_effect = populate_interface_list
    with patch("rpi_dashboard.services.system.ctypes.CDLL", return_value=libc):
        result = system._get_interface_addresses_native()

    libc.freeifaddrs.assert_called_once()
    assert result == [
        "192.168.0.100",
        "192.168.0.101",
        "100.64.0.2",
        "2001:db8::1",
    ]


def test_native_default_gateway_uses_active_route_with_lowest_metric():
    """Choose the active default route with the lowest metric."""
    from rpi_dashboard.services.system import _get_default_gateway_native

    routes = (
        "Iface Destination Gateway Flags RefCnt Use Metric Mask MTU Window IRTT\n"
        "vpn0 00000000 0201A8C0 0003 0 0 1 00800000 0 0 0\n"
        "eth0 00000000 0102A8C0 0003 0 0 100 00000000 0 0 0\n"
        "wlan0 00000000 0101A8C0 0003 0 0 10 00000000 0 0 0\n"
        "down0 00000000 0101A8C0 0002 0 0 1 00000000 0 0 0\n"
        "none0 00000000 00000000 0003 0 0 0 00000000 0 0 0\n"
    )
    with patch("builtins.open", mock_open(read_data=routes)):
        result = _get_default_gateway_native()

    assert result == "192.168.1.1"


def test_dashboard_hostnames_and_ips_tolerate_tailscale_failures():
    """Network discovery should tolerate transient Tailscale outages."""
    from rpi_dashboard.services.system import dashboard_hostnames_and_ips

    with patch("rpi_dashboard.services.system.socket.gethostname", return_value="rpi-tv"):
        with patch("rpi_dashboard.services.system._get_interface_addresses_native", return_value=["192.168.0.100"]):
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

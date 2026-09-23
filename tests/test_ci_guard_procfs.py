from unittest.mock import mock_open, patch, MagicMock
from rpi_dashboard.ci.rpi_guard import RPiGuard

def test_get_processes_native_procfs():
    guard = RPiGuard()

    mock_listdir = MagicMock(return_value=["1", "2", "non_numeric"])

    def fake_open(filepath, mode="r", *args, **kwargs):
        if filepath == "/proc/uptime":
            return mock_open(read_data="1000.0 500.0").return_value
        elif filepath == "/proc/1/stat":
            return mock_open(read_data="1 (systemd) S 0 1 1 0 -1 4194560 0 0 0 0 100 200 0 0 20 0 1 0 500").return_value
        elif filepath == "/proc/1/cmdline":
            return mock_open(read_data=b"/sbin/init\x00arg1\x00").return_value
        elif filepath == "/proc/2/stat":
            return mock_open(read_data="2 (kthreadd) S 0 0 0 0 -1 0 0 0 0 0 10 20 0 0 20 0 1 0 1000").return_value
        elif filepath == "/proc/2/cmdline":
            return mock_open(read_data=b"").return_value
        raise OSError("File not found")

    with patch("os.listdir", mock_listdir):
        with patch("builtins.open", side_effect=fake_open):
            with patch("os.sysconf", return_value=100):
                procs = guard._get_processes()

    assert len(procs) == 2

    p1 = procs[0]
    assert p1["pid"] == 1
    assert p1["ppid"] == 0
    assert p1["comm"] == "systemd"
    assert p1["args"] == "/sbin/init arg1"
    assert p1["pcpu"] > 0.0

    p2 = procs[1]
    assert p2["pid"] == 2
    assert p2["comm"] == "kthreadd"
    assert p2["args"] == "[kthreadd]"


def test_get_processes_native_procfs_errors():
    guard = RPiGuard()

    mock_listdir = MagicMock(return_value=["1", "2"])

    def fake_open(filepath, mode="r", *args, **kwargs):
        if filepath == "/proc/uptime":
            return mock_open(read_data="1000.0 500.0").return_value
        elif filepath == "/proc/1/stat":
            # Missing parenthesis
            return mock_open(read_data="1 systemd S 0").return_value
        elif filepath == "/proc/2/stat":
            # Correct parens but not enough fields
            return mock_open(read_data="2 (kthreadd) S 0").return_value
        raise OSError("File not found")

    with patch("os.listdir", mock_listdir):
        with patch("builtins.open", side_effect=fake_open):
            with patch("os.sysconf", return_value=100):
                procs = guard._get_processes()

    assert len(procs) == 0

def test_get_processes_native_procfs_no_uptime():
    guard = RPiGuard()

    def fake_open(filepath, mode="r", *args, **kwargs):
        if filepath == "/proc/uptime":
            raise OSError("No uptime")
        return mock_open(read_data="").return_value

    with patch("builtins.open", side_effect=fake_open):
        procs = guard._get_processes()

    assert len(procs) == 0

def test_get_processes_native_procfs_cmdline_error():
    guard = RPiGuard()
    mock_listdir = MagicMock(return_value=["1"])

    def fake_open(filepath, mode="r", *args, **kwargs):
        if filepath == "/proc/uptime":
            return mock_open(read_data="1000.0 500.0").return_value
        elif filepath == "/proc/1/stat":
            return mock_open(read_data="1 (systemd) S 0 1 1 0 -1 4194560 0 0 0 0 100 200 0 0 20 0 1 0 500").return_value
        elif filepath == "/proc/1/cmdline":
            raise OSError("No cmdline")
        raise OSError("File not found")

    with patch("os.listdir", mock_listdir):
        with patch("builtins.open", side_effect=fake_open):
            with patch("os.sysconf", side_effect=Exception("No sysconf")):
                procs = guard._get_processes()

    assert len(procs) == 1
    assert procs[0]["comm"] == "systemd"
    assert procs[0]["args"] == "[systemd]"


def test_get_current_pid_family_procfs():
    from rpi_dashboard.ci.rpi_guard import get_current_pid_family

    def fake_open(filepath, mode="r", *args, **kwargs):
        if filepath == "/proc/123/stat":
            return mock_open(read_data="123 (python3) S 456").return_value
        elif filepath == "/proc/456/stat":
            return mock_open(read_data="456 (bash) S 1").return_value
        elif filepath == "/proc/1/stat":
            return mock_open(read_data="1 (systemd) S 0").return_value
        raise OSError("File not found")

    with patch("os.getpid", return_value=123):
        with patch("builtins.open", side_effect=fake_open):
            pids = get_current_pid_family()

    assert pids == {123, 456}

def test_get_current_pid_family_procfs_error():
    from rpi_dashboard.ci.rpi_guard import get_current_pid_family

    def fake_open(filepath, mode="r", *args, **kwargs):
        raise OSError("File not found")

    with patch("os.getpid", return_value=123):
        with patch("builtins.open", side_effect=fake_open):
            pids = get_current_pid_family()

    assert pids == {123}

def test_check_status_sustained_cpu():
    guard = RPiGuard()

    def mock_get_processes():
        return [
            {"pid": 100, "comm": "mpv", "pcpu": 50.0, "args": "mpv video.mp4"},
            {"pid": 101, "comm": "python3", "pcpu": 10.0, "args": "python3 script.py"}
        ]

    guard._get_processes = mock_get_processes

    # Just to get some coverage for the check_status routine
    status = guard.check_status(exclude_pids={101}, sustained_cpu_samples=1)

    assert status.get("user_cpu_pct") == 50.0

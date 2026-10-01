import pytest
from unittest.mock import patch, mock_open
from rpi_dashboard.ci.rpi_guard import parse_proc_ps_output, RPiGuard, RPiBusyError

def test_rpi_guard_proc_provider():
    guard = RPiGuard(proc_provider=lambda: [{"pid": 123}])
    assert guard._get_processes() == [{"pid": 123}]

def test_parse_proc_ps_output_empty():
    assert parse_proc_ps_output("") == []

def test_rpi_guard_get_processes_native():
    guard = RPiGuard()

    mock_uptime = "100.0 200.0"
    mock_stat = "1 (systemd) S 0 1 1 0 -1 4194560 62114 62450530 46 1794 85 401 270 2932 20 0 1 0 17 25292800 1342 18446744073709551615 1 1 0 0 0 0 0 4096 536962595 1 0 0 17 1 0 0 0 0 0 0 0 0 0 0 0 0 0"
    mock_cmdline = b"/lib/systemd/systemd\x00--system\x00--deserialize\x0014\x00"

    def fake_open(filename, *args, **kwargs):
        if filename == '/proc/uptime':
            return mock_open(read_data=mock_uptime).return_value
        elif filename == '/proc/1/stat':
            return mock_open(read_data=mock_stat).return_value
        elif filename == '/proc/1/cmdline':
            return mock_open(read_data=mock_cmdline).return_value
        elif 'stat' in filename or 'cmdline' in filename:
            raise FileNotFoundError()
        raise FileNotFoundError(f"Missing fake for {filename}")

    with patch('os.listdir', return_value=['1', 'not_a_pid']):
        with patch('builtins.open', side_effect=fake_open):
            with patch('os.sysconf', return_value=100.0):
                procs = guard._get_processes()

                assert len(procs) == 1
                assert procs[0]['pid'] == 1
                assert procs[0]['ppid'] == 0
                assert procs[0]['comm'] == 'systemd'
                assert procs[0]['args'] == '/lib/systemd/systemd --system --deserialize 14'
                assert procs[0]['pcpu'] > 0

def test_rpi_guard_get_processes_native_exception():
    guard = RPiGuard()

    def fake_open(filename, *args, **kwargs):
        raise FileNotFoundError()

    with patch('os.listdir', return_value=['1']):
        with patch('builtins.open', side_effect=fake_open):
            procs = guard._get_processes()
            assert procs == []

def test_rpi_guard_get_processes_native_skip_non_digits():
    guard = RPiGuard()

    mock_uptime = "100.0 200.0"

    def fake_open(filename, *args, **kwargs):
        if filename == '/proc/uptime':
            return mock_open(read_data=mock_uptime).return_value
        raise FileNotFoundError(f"Missing fake for {filename}")

    with patch('os.listdir', return_value=['not_a_pid', 'abc']):
        with patch('builtins.open', side_effect=fake_open):
            with patch('os.sysconf', return_value=100.0):
                procs = guard._get_processes()
                assert procs == []

def test_rpi_guard_get_processes_native_no_cmdline():
    guard = RPiGuard()

    mock_uptime = "100.0 200.0"
    mock_stat = "1 (systemd) S 0 1 1 0 -1 4194560 62114 62450530 46 1794 85 401 270 2932 20 0 1 0 17 25292800 1342 18446744073709551615 1 1 0 0 0 0 0 4096 536962595 1 0 0 17 1 0 0 0 0 0 0 0 0 0 0 0 0 0"

    def fake_open(filename, *args, **kwargs):
        if filename == '/proc/uptime':
            return mock_open(read_data=mock_uptime).return_value
        elif filename == '/proc/1/stat':
            return mock_open(read_data=mock_stat).return_value
        elif filename == '/proc/1/cmdline':
            raise FileNotFoundError()
        raise FileNotFoundError(f"Missing fake for {filename}")

    with patch('os.listdir', return_value=['1']):
        with patch('builtins.open', side_effect=fake_open):
            with patch('os.sysconf', return_value=100.0):
                procs = guard._get_processes()

                assert len(procs) == 1
                assert procs[0]['pid'] == 1
                assert procs[0]['comm'] == 'systemd'
                assert procs[0]['args'] == 'systemd'

def test_rpi_guard_get_processes_native_negative_time():
    guard = RPiGuard()

    mock_uptime = "0.0 200.0"
    mock_stat = "1 (systemd) S 0 1 1 0 -1 4194560 62114 62450530 46 1794 85 401 270 2932 20 0 1 0 17 25292800 1342 18446744073709551615 1 1 0 0 0 0 0 4096 536962595 1 0 0 17 1 0 0 0 0 0 0 0 0 0 0 0 0 0"

    def fake_open(filename, *args, **kwargs):
        if filename == '/proc/uptime':
            return mock_open(read_data=mock_uptime).return_value
        elif filename == '/proc/1/stat':
            return mock_open(read_data=mock_stat).return_value
        elif filename == '/proc/1/cmdline':
            raise FileNotFoundError()
        raise FileNotFoundError(f"Missing fake for {filename}")

    with patch('os.listdir', return_value=['1']):
        with patch('builtins.open', side_effect=fake_open):
            with patch('os.sysconf', return_value=100.0):
                procs = guard._get_processes()

                assert len(procs) == 1
                assert procs[0]['pid'] == 1
                assert procs[0]['pcpu'] == 0.0

def test_rpi_guard_get_processes_native_skip_non_digits2():
    guard = RPiGuard()

    mock_uptime = "100.0 200.0"
    mock_stat = "1 (systemd) S 0 1 1 0 -1 4194560 62114 62450530 46 1794 85 401 270 2932 20 0 1 0 17 25292800 1342 18446744073709551615 1 1 0 0 0 0 0 4096 536962595 1 0 0 17 1 0 0 0 0 0 0 0 0 0 0 0 0 0"
    mock_cmdline = b"/lib/systemd/systemd\x00--system\x00--deserialize\x0014\x00"

    def fake_open(filename, *args, **kwargs):
        if filename == '/proc/uptime':
            return mock_open(read_data=mock_uptime).return_value
        elif filename == '/proc/1/stat':
            return mock_open(read_data=mock_stat).return_value
        elif filename == '/proc/1/cmdline':
            return mock_open(read_data=mock_cmdline).return_value
        raise FileNotFoundError(f"Missing fake for {filename}")

    with patch('os.listdir', return_value=['not_a_pid', '1']):
        with patch('builtins.open', side_effect=fake_open):
            with patch('os.sysconf', return_value=100.0):
                procs = guard._get_processes()
                assert len(procs) == 1

def test_rpi_guard_get_processes_native_negative_time2():
    guard = RPiGuard()

    mock_uptime = "100.0 200.0"
    mock_stat = "1 (systemd) S 0 1 1 0 -1 4194560 62114 62450530 46 1794 85 401 270 2932 20 0 1 0 17 25292800 1342 18446744073709551615 1 1 0 0 0 0 0 4096 536962595 1 0 0 17 1 0 0 0 0 0 0 0 0 0 0 0 0 0"
    mock_cmdline = b"/lib/systemd/systemd\x00--system\x00--deserialize\x0014\x00"

    def fake_open(filename, *args, **kwargs):
        if filename == '/proc/uptime':
            raise Exception("Force general exception path")
        raise FileNotFoundError(f"Missing fake for {filename}")

    with patch('os.listdir', return_value=['1']):
        with patch('builtins.open', side_effect=fake_open):
            with patch('os.sysconf', return_value=100.0):
                procs = guard._get_processes()
                assert procs == []

def test_rpi_guard_get_processes_native_skip_non_digits3():
    guard = RPiGuard()
    mock_uptime = "100.0 200.0"
    def fake_open(filename, *args, **kwargs):
        if filename == '/proc/uptime':
            return mock_open(read_data=mock_uptime).return_value
        raise FileNotFoundError(f"Missing fake for {filename}")

    with patch('os.listdir', return_value=['not_a_pid', 'abc', '1abc']):
        with patch('builtins.open', side_effect=fake_open):
            procs = guard._get_processes()
            assert procs == []

def test_rpi_guard_get_processes_native_skip_non_digits4():
    guard = RPiGuard()
    mock_uptime = "100.0 200.0"
    def fake_open(filename, *args, **kwargs):
        raise FileNotFoundError(f"Missing fake for {filename}")

    with patch('os.listdir', return_value=[]):
        with patch('builtins.open', side_effect=fake_open):
            procs = guard._get_processes()
            assert procs == []

def test_rpi_guard_get_processes_native_skip_non_digits5():
    guard = RPiGuard()
    mock_uptime = "100.0 200.0"
    def fake_open(filename, *args, **kwargs):
        if filename == '/proc/uptime':
            return mock_open(read_data=mock_uptime).return_value
        elif filename == '/proc/1/stat':
            return mock_open(read_data="1 (systemd) S").return_value
        raise FileNotFoundError(f"Missing fake for {filename}")

    with patch('os.listdir', return_value=['1']):
        with patch('builtins.open', side_effect=fake_open):
            with patch('os.sysconf', return_value=100.0):
                procs = guard._get_processes()
                assert procs == []

def test_rpi_guard_get_processes_native_negative_time3():
    guard = RPiGuard()

    mock_uptime = "100.0 200.0"
    mock_stat = "1 (systemd) S 0 1 1 0 -1 4194560 62114 62450530 46 1794 85 401 270 2932 20 0 1 0 17 25292800 1342 18446744073709551615 1 1 0 0 0 0 0 4096 536962595 1 0 0 17 1 0 0 0 0 0 0 0 0 0 0 0 0 0"
    mock_cmdline = b""

    def fake_open(filename, *args, **kwargs):
        if filename == '/proc/uptime':
            return mock_open(read_data=mock_uptime).return_value
        elif filename == '/proc/1/stat':
            return mock_open(read_data=mock_stat).return_value
        elif filename == '/proc/1/cmdline':
            return mock_open(read_data=mock_cmdline).return_value
        raise FileNotFoundError(f"Missing fake for {filename}")

    with patch('os.listdir', return_value=['1']):
        with patch('builtins.open', side_effect=fake_open):
            with patch('os.sysconf', return_value=100.0):
                procs = guard._get_processes()
                assert len(procs) == 1
                assert procs[0]['args'] == 'systemd'

def test_rpi_guard_get_processes_native_negative_time4():
    guard = RPiGuard()

    mock_uptime = "100.0 200.0"
    mock_stat = "1 (systemd) S 0 1 1 0 -1 4194560 62114 62450530 46 1794 85 401 270 2932 20 0 1 0 17 25292800 1342 18446744073709551615 1 1 0 0 0 0 0 4096 536962595 1 0 0 17 1 0 0 0 0 0 0 0 0 0 0 0 0 0"

    def fake_open(filename, *args, **kwargs):
        if filename == '/proc/uptime':
            return mock_open(read_data=mock_uptime).return_value
        elif filename == '/proc/1/stat':
            raise Exception("Force exception on stat read")
        raise FileNotFoundError(f"Missing fake for {filename}")

    with patch('os.listdir', return_value=['1']):
        with patch('builtins.open', side_effect=fake_open):
            with patch('os.sysconf', return_value=100.0):
                procs = guard._get_processes()
                assert procs == []

def test_rpi_guard_get_processes_native_skip_non_digits6():
    guard = RPiGuard()
    mock_uptime = "100.0 200.0"
    def fake_open(filename, *args, **kwargs):
        if filename == '/proc/uptime':
            return mock_open(read_data=mock_uptime).return_value
        elif filename == '/proc/1/stat':
            raise Exception("Force general exception path on stat")
        raise FileNotFoundError(f"Missing fake for {filename}")

    with patch('os.listdir', return_value=['1']):
        with patch('builtins.open', side_effect=fake_open):
            with patch('os.sysconf', return_value=100.0):
                procs = guard._get_processes()
                assert procs == []

def test_rpi_guard_get_processes_native_skip_non_digits7():
    guard = RPiGuard()
    mock_uptime = "100.0 200.0"
    def fake_open(filename, *args, **kwargs):
        if filename == '/proc/uptime':
            return mock_open(read_data=mock_uptime).return_value
        elif filename == '/proc/1/stat':
            raise IOError("Force general exception path on stat")
        raise FileNotFoundError(f"Missing fake for {filename}")

    with patch('os.listdir', return_value=['1']):
        with patch('builtins.open', side_effect=fake_open):
            with patch('os.sysconf', return_value=100.0):
                procs = guard._get_processes()
                assert procs == []

def test_rpi_guard_get_processes_native_negative_time5():
    guard = RPiGuard()

    mock_uptime = "100.0 200.0"
    mock_stat = "1 (systemd) S 0 1 1 0 -1 4194560 62114 62450530 46 1794 85 401 270 2932 20 0 1 0 17 25292800 1342 18446744073709551615 1 1 0 0 0 0 0 4096 536962595 1 0 0 17 1 0 0 0 0 0 0 0 0 0 0 0 0 0"

    def fake_open(filename, *args, **kwargs):
        if filename == '/proc/uptime':
            return mock_open(read_data=mock_uptime).return_value
        elif filename == '/proc/1/stat':
            raise ValueError("Force ValueError exception on stat read")
        raise FileNotFoundError(f"Missing fake for {filename}")

    with patch('os.listdir', return_value=['1']):
        with patch('builtins.open', side_effect=fake_open):
            with patch('os.sysconf', return_value=100.0):
                procs = guard._get_processes()
                assert procs == []

def test_rpi_guard_get_processes_native_skip_non_digits8():
    guard = RPiGuard()
    mock_uptime = "100.0 200.0"
    mock_stat = "1 (systemd) S 0 1 1 0 -1 4194560 62114 62450530 46 1794 85 401 270 2932 20 0 1 0 17 25292800 1342 18446744073709551615 1 1 0 0 0 0 0 4096 536962595 1 0 0 17 1 0 0 0 0 0 0 0 0 0 0 0 0 0"

    def fake_open(filename, *args, **kwargs):
        if filename == '/proc/uptime':
            return mock_open(read_data=mock_uptime).return_value
        elif filename == '/proc/1/stat':
            return mock_open(read_data=mock_stat).return_value
        elif filename == '/proc/1/cmdline':
            raise IOError("Force IOError exception on cmdline read")
        raise FileNotFoundError(f"Missing fake for {filename}")

    with patch('os.listdir', return_value=['1']):
        with patch('builtins.open', side_effect=fake_open):
            with patch('os.sysconf', return_value=100.0):
                procs = guard._get_processes()
                assert len(procs) == 1
                assert procs[0]['args'] == 'systemd'

def test_rpi_guard_get_processes_native_skip_non_digits9():
    guard = RPiGuard()
    mock_uptime = "100.0 200.0"
    mock_stat = "1 (systemd) S 0 1 1 0 -1 4194560 62114 62450530 46 1794 85 401 270 2932 20 0 1 0 17 25292800 1342 18446744073709551615 1 1 0 0 0 0 0 4096 536962595 1 0 0 17 1 0 0 0 0 0 0 0 0 0 0 0 0 0"

    def fake_open(filename, *args, **kwargs):
        if filename == '/proc/uptime':
            return mock_open(read_data=mock_uptime).return_value
        elif filename == '/proc/1/stat':
            return mock_open(read_data=mock_stat).return_value
        elif filename == '/proc/1/cmdline':
            raise Exception("Force exception on cmdline read")
        raise FileNotFoundError(f"Missing fake for {filename}")

    with patch('os.listdir', return_value=['1']):
        with patch('builtins.open', side_effect=fake_open):
            with patch('os.sysconf', return_value=100.0):
                procs = guard._get_processes()
                assert len(procs) == 1
                assert procs[0]['args'] == 'systemd'

def test_rpi_guard_get_processes_native_skip_non_digits10():
    guard = RPiGuard()
    mock_uptime = "100.0 200.0"
    mock_stat = "1 (systemd) S 0 1 1 0 -1 4194560 62114 62450530 46 1794 85 401 270 2932 20 0 1 0 17 25292800 1342 18446744073709551615 1 1 0 0 0 0 0 4096 536962595 1 0 0 17 1 0 0 0 0 0 0 0 0 0 0 0 0 0"
    mock_cmdline = b"/lib/systemd/systemd\x00--system\x00--deserialize\x0014\x00"

    def fake_open(filename, *args, **kwargs):
        if filename == '/proc/uptime':
            return mock_open(read_data=mock_uptime).return_value
        elif filename == '/proc/1/stat':
            return mock_open(read_data=mock_stat).return_value
        elif filename == '/proc/1/cmdline':
            return mock_open(read_data=mock_cmdline).return_value
        elif filename == '/proc/2/stat':
            raise Exception("Force second element fail")
        raise FileNotFoundError(f"Missing fake for {filename}")

    with patch('os.listdir', return_value=['1', '2']):
        with patch('builtins.open', side_effect=fake_open):
            with patch('os.sysconf', return_value=100.0):
                procs = guard._get_processes()
                assert len(procs) == 1

def test_rpi_guard_get_processes_native_skip_non_digits11():
    guard = RPiGuard()
    mock_uptime = "100.0 200.0"
    mock_stat = "1 (systemd) S 0 1 1 0 -1 4194560 62114 62450530 46 1794 85 401 270 2932 20 0 1 0 17 25292800 1342 18446744073709551615 1 1 0 0 0 0 0 4096 536962595 1 0 0 17 1 0 0 0 0 0 0 0 0 0 0 0 0 0"
    mock_cmdline = b"/lib/systemd/systemd\x00--system\x00--deserialize\x0014\x00"

    def fake_open(filename, *args, **kwargs):
        if filename == '/proc/uptime':
            return mock_open(read_data=mock_uptime).return_value
        elif filename == '/proc/1/stat':
            return mock_open(read_data=mock_stat).return_value
        elif filename == '/proc/1/cmdline':
            return mock_open(read_data=mock_cmdline).return_value
        raise FileNotFoundError(f"Missing fake for {filename}")

    with patch('os.listdir', return_value=['1']):
        with patch('builtins.open', side_effect=fake_open):
            with patch('os.sysconf', return_value=100.0):
                procs = guard._get_processes()
                assert len(procs) == 1

def test_rpi_guard_get_ram_free_mb_provider():
    guard = RPiGuard(ram_provider=lambda: 512.0)
    assert guard._get_ram_free_mb() == 512.0

def test_rpi_guard_get_processes_native_skip_non_digits12():
    guard = RPiGuard()
    mock_uptime = "100.0 200.0"
    mock_stat = "1 (systemd) S 0 1 1 0 -1 4194560 62114 62450530 46 1794 85 401 270 2932 20 0 1 0 17 25292800 1342 18446744073709551615 1 1 0 0 0 0 0 4096 536962595 1 0 0 17 1 0 0 0 0 0 0 0 0 0 0 0 0 0"

    def fake_open(filename, *args, **kwargs):
        if filename == '/proc/uptime':
            return mock_open(read_data=mock_uptime).return_value
        elif filename == '/proc/1/stat':
            return mock_open(read_data=mock_stat).return_value
        elif filename == '/proc/1/cmdline':
            raise OSError("Force OSError exception on cmdline read")
        raise FileNotFoundError(f"Missing fake for {filename}")

    with patch('os.listdir', return_value=['1']):
        with patch('builtins.open', side_effect=fake_open):
            with patch('os.sysconf', return_value=100.0):
                procs = guard._get_processes()
                assert len(procs) == 1
                assert procs[0]['args'] == 'systemd'

def test_rpi_guard_get_processes_native_skip_non_digits13():
    guard = RPiGuard()
    mock_uptime = "100.0 200.0"

    def fake_open(filename, *args, **kwargs):
        if filename == '/proc/uptime':
            return mock_open(read_data=mock_uptime).return_value
        elif filename == '/proc/1/stat':
            raise OSError("Force OSError exception on stat read")
        raise FileNotFoundError(f"Missing fake for {filename}")

    with patch('os.listdir', return_value=['1']):
        with patch('builtins.open', side_effect=fake_open):
            with patch('os.sysconf', return_value=100.0):
                procs = guard._get_processes()
                assert procs == []

def test_rpi_guard_run_protected_command2():
    guard = RPiGuard(proc_provider=lambda: [{"pid": 123, "comm": "mpv", "pcpu": 50.0}])

    with pytest.raises(RPiBusyError):
        guard.run_protected_command(["ls"])

def test_rpi_guard_check_status():
    guard = RPiGuard(proc_provider=lambda: [{"pid": 123, "comm": "mpv", "pcpu": 50.0}])
    status = guard.check_status()
    assert status['busy'] is True

def test_rpi_guard_check_status_not_busy():
    guard = RPiGuard(proc_provider=lambda: [])
    status = guard.check_status()
    assert status['busy'] is False

def test_rpi_guard_run_protected_command_exception():
    guard = RPiGuard(proc_provider=lambda: [{"pid": 123, "comm": "mpv", "pcpu": 50.0}])

    with pytest.raises(RPiBusyError):
        guard.run_protected_command(["ls"])

def test_rpi_guard_run_protected_command_timeout():
    from rpi_dashboard.ci.rpi_guard import RPiPlaybackStartedInterrupt
    # Start idle, then busy to trigger timeout
    state = {"count": 0}
    def dynamic_provider():
        if state["count"] == 0:
            state["count"] += 1
            return []
        return [{"pid": 123, "comm": "mpv", "pcpu": 50.0}]

    guard = RPiGuard(proc_provider=dynamic_provider)

    with patch('subprocess.Popen') as mock_popen, patch('time.sleep', return_value=None), patch('time.time', side_effect=[0, 1, 2, 3, 4, 100]):
        mock_popen.return_value.poll.return_value = None # Force it to stay "running" so we hit the check loop
        mock_popen.return_value.communicate.return_value = ("out", "err")
        with pytest.raises(RPiPlaybackStartedInterrupt) as e:
            guard.run_protected_command(["ls"], cancel_callback=lambda: None)

    assert "aborted candidate process" in str(e.value)

def test_rpi_guard_get_sustained_user_cpu_pct():
    guard = RPiGuard(proc_provider=lambda: [{"pid": 123, "comm": "app", "pcpu": 10.0}])
    with patch('time.sleep', return_value=None):
        pct = guard._get_sustained_user_cpu_pct(set([999]), sample_count=2, sample_delay=0.1)
        assert pct == 10.0

def test_rpi_guard_wait_until_idle():
    guard = RPiGuard(proc_provider=lambda: [])
    with patch('rpi_dashboard.ci.rpi_guard.get_active_mode', return_value='none'), patch('time.sleep', return_value=None), patch('time.time', side_effect=[0, 100]):
        status = guard.wait_until_idle()
        assert status['busy'] is False

def test_rpi_guard_run_protected_command_terminate_success():
    from rpi_dashboard.ci.rpi_guard import RPiPlaybackStartedInterrupt
    # Start idle, then busy to trigger timeout
    state = {"count": 0}
    def dynamic_provider():
        if state["count"] == 0:
            state["count"] += 1
            return []
        return [{"pid": 123, "comm": "mpv", "pcpu": 50.0}]

    guard = RPiGuard(proc_provider=dynamic_provider)

    with patch('subprocess.Popen') as mock_popen, patch('time.sleep', return_value=None), patch('time.time', side_effect=[0, 1, 2, 3, 4, 100]):
        mock_popen.return_value.poll.return_value = None # Force it to stay "running" so we hit the check loop
        mock_popen.return_value.communicate.return_value = ("out", "err")
        mock_popen.return_value.wait.return_value = 0 # No TimeoutExpired
        with pytest.raises(RPiPlaybackStartedInterrupt) as e:
            guard.run_protected_command(["ls"], cancel_callback=lambda: None)

    assert "aborted candidate process" in str(e.value)
    mock_popen.return_value.terminate.assert_called()

def test_rpi_guard_run_protected_command_terminate_timeout():
    from rpi_dashboard.ci.rpi_guard import RPiPlaybackStartedInterrupt
    import subprocess
    # Start idle, then busy to trigger timeout
    state = {"count": 0}
    def dynamic_provider():
        if state["count"] == 0:
            state["count"] += 1
            return []
        return [{"pid": 123, "comm": "mpv", "pcpu": 50.0}]

    guard = RPiGuard(proc_provider=dynamic_provider)

    with patch('subprocess.Popen') as mock_popen, patch('time.sleep', return_value=None), patch('time.time', side_effect=[0, 1, 2, 3, 4, 100]):
        mock_popen.return_value.poll.return_value = None # Force it to stay "running" so we hit the check loop
        mock_popen.return_value.communicate.return_value = ("out", "err")
        mock_popen.return_value.wait.side_effect = subprocess.TimeoutExpired(cmd="ls", timeout=2.0)
        with pytest.raises(RPiPlaybackStartedInterrupt) as e:
            guard.run_protected_command(["ls"], cancel_callback=lambda: None)

    assert "aborted candidate process" in str(e.value)
    mock_popen.return_value.terminate.assert_called()
    mock_popen.return_value.kill.assert_called()

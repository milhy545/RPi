# pylint: disable=missing-function-docstring,redefined-outer-name,protected-access,import-outside-toplevel,wrong-import-order,missing-class-docstring,missing-module-docstring,too-few-public-methods,line-too-long,trailing-whitespace,multiple-statements,use-implicit-booleaness-not-comparison
import pytest
import asyncio
import signal
from unittest.mock import Mock, patch, AsyncMock
from mode_switcher import ModeSwitcher, ModeSwitcherState, InvalidTransition, LogBuffer

class MockApp:
    def __init__(self):
        self.exit_called = False
        self.pause_api_server_called = False
        self.resume_api_server_called = False
        self.replay_log_buffer_called = False
        self.suspend_error = None

    def exit(self):
        self.exit_called = True

    def pause_api_server(self):
        self.pause_api_server_called = True

    def resume_api_server(self):
        self.resume_api_server_called = True

    def replay_log_buffer(self):
        self.replay_log_buffer_called = True

    def suspend(self):
        if self.suspend_error:
            raise self.suspend_error

        class DummyContextManager:
            def __enter__(self): pass
            def __exit__(self, exc_type, exc_val, exc_tb): pass
        return DummyContextManager()

@pytest.fixture
def mock_app():
    return MockApp()

@pytest.fixture
def mode_switcher(mock_app):
    return ModeSwitcher(mock_app)

def test_log_buffer():
    lb = LogBuffer(max_lines=2)
    lb.write("1")
    lb.write("2")
    assert lb.get_lines() == ["1", "2"]
    lb.write("3")
    assert lb.get_lines() == ["2", "3"]
    lb.clear()
    assert lb.get_lines() == []

def test_initial_state(mode_switcher):
    assert mode_switcher.state == ModeSwitcherState.IDLE
    assert isinstance(mode_switcher.log_buffer, LogBuffer)
    assert mode_switcher.active_process is None
    assert mode_switcher.watchdog_task is None

def test_valid_transitions(mode_switcher):
    mode_switcher._transition(ModeSwitcherState.SUSPENDING)
    assert mode_switcher.state == ModeSwitcherState.SUSPENDING

    mode_switcher._transition(ModeSwitcherState.RUNNING)
    assert mode_switcher.state == ModeSwitcherState.RUNNING

    mode_switcher._transition(ModeSwitcherState.RESUMING)
    assert mode_switcher.state == ModeSwitcherState.RESUMING

    mode_switcher._transition(ModeSwitcherState.IDLE)
    assert mode_switcher.state == ModeSwitcherState.IDLE

def test_invalid_transitions(mode_switcher):
    # IDLE -> RUNNING is invalid
    with pytest.raises(InvalidTransition):
        mode_switcher._transition(ModeSwitcherState.RUNNING)

    # IDLE -> RESUMING is invalid
    with pytest.raises(InvalidTransition):
        mode_switcher._transition(ModeSwitcherState.RESUMING)

@pytest.mark.asyncio
async def test_launch_success(mode_switcher, mock_app):
    with patch("subprocess.Popen") as mock_popen:
        mock_process = Mock()
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        success = await mode_switcher.launch(["echo", "test"])

        assert success is True
        assert mode_switcher.state == ModeSwitcherState.IDLE
        mock_popen.assert_called_once()
        assert mock_app.pause_api_server_called is True
        assert mock_app.resume_api_server_called is True
        assert mock_app.replay_log_buffer_called is True

@pytest.mark.asyncio
async def test_launch_concurrency_guard(mode_switcher):
    with patch("subprocess.Popen") as mock_popen:
        mock_process = Mock()
        # Make the first command wait a bit
        def mock_wait():
            import time
            time.sleep(0.5)
            return 0
        mock_process.wait.side_effect = mock_wait
        mock_popen.return_value = mock_process

        # Launch the first process
        task1 = asyncio.create_task(mode_switcher.launch(["echo", "first"]))

        # Wait a tiny bit to ensure the first process is running and state changed
        await asyncio.sleep(0.1)

        # Try to launch a second process concurrently
        success2 = await mode_switcher.launch(["echo", "second"])

        # The second process should be rejected immediately
        assert success2 is False

        # Wait for the first process to finish
        success1 = await task1

        # The first process should succeed
        assert success1 is True

@pytest.mark.asyncio
async def test_launch_with_exception(mode_switcher):
    with patch("subprocess.Popen") as mock_popen:
        mock_process = Mock()
        mock_process.wait.side_effect = Exception("Test Error")
        mock_popen.return_value = mock_process

        success = await mode_switcher.launch(["echo", "test"])

        assert success is False
        assert mode_switcher.state == ModeSwitcherState.IDLE
        assert any("Subprocess exception" in log for log in mode_switcher.log_buffer.get_lines())

@pytest.mark.asyncio
async def test_launch_suspend_exception_fallback(mode_switcher, mock_app):
    with patch("subprocess.Popen") as mock_popen:
        mock_process = Mock()
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        # Trigger fallback
        mock_app.suspend_error = Exception("App.suspend not supported in this environment")

        success = await mode_switcher.launch(["echo", "test"])

        assert success is True
        assert any("App.suspend not supported" in log for log in mode_switcher.log_buffer.get_lines())

@pytest.mark.asyncio
async def test_launch_suspend_exception_other(mode_switcher, mock_app):
    # If the suspend context manager raises a totally different error, it should be caught by the outer block
    mock_app.suspend_error = Exception("Some weird error")
    success = await mode_switcher.launch(["echo", "test"])

    # Process exit code becomes -1
    assert success is False
    assert any("Suspension block execution failed" in log for log in mode_switcher.log_buffer.get_lines())

@pytest.mark.asyncio
async def test_watchdog_timeout(mode_switcher):
    with patch("subprocess.Popen") as mock_popen:
        mock_process = Mock()
        def mock_wait():
            import time
            time.sleep(0.5)
            return 0
        mock_process.wait.side_effect = mock_wait
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        mode_switcher._teardown_active_process = AsyncMock()
        task = asyncio.create_task(mode_switcher.launch(["echo", "test"], timeout=0.1))
        await asyncio.sleep(0.2)
        mode_switcher._teardown_active_process.assert_called_once()
        assert any("Watchdog fired" in log for log in mode_switcher.log_buffer.get_lines())

        await task

@pytest.mark.asyncio
async def test_watchdog_timer_cancellation(mode_switcher):
    mode_switcher._teardown_active_process = AsyncMock()
    # Explicitly test the CancelledError path in _watchdog_timer
    task = asyncio.create_task(mode_switcher._watchdog_timer(0.5))
    await asyncio.sleep(0.1)
    task.cancel()
    await task
    mode_switcher._teardown_active_process.assert_not_called()

@pytest.mark.asyncio
async def test_teardown_active_process(mode_switcher):
    mock_process = Mock()
    mock_process.poll.side_effect = [None, None, 0, 0, 0, 0, 0] # First None, then None, then 0 (terminated)
    mode_switcher.active_process = mock_process

    await mode_switcher._teardown_active_process()

    mock_process.terminate.assert_called_once()
    mock_process.kill.assert_not_called()
    assert any("Terminating active subprocess..." in log for log in mode_switcher.log_buffer.get_lines())

@pytest.mark.asyncio
async def test_teardown_active_process_force_kill(mode_switcher):
    mock_process = Mock()
    # Always return None for poll, meaning it never gracefully terminates
    mock_process.poll.return_value = None
    mode_switcher.active_process = mock_process

    with patch("asyncio.sleep", return_value=None) as mock_sleep:
        await mode_switcher._teardown_active_process()

    mock_process.terminate.assert_called_once()
    mock_process.kill.assert_called_once()
    logs = mode_switcher.log_buffer.get_lines()
    assert any("Subprocess did not terminate. Killing..." in log for log in logs)
    assert mock_sleep.call_count == 30

@pytest.mark.asyncio
async def test_sigterm_handling(mode_switcher):
    mode_switcher._transition(ModeSwitcherState.SUSPENDING)
    mode_switcher._transition(ModeSwitcherState.RUNNING)
    mode_switcher._teardown_and_exit = AsyncMock()

    mode_switcher._loop = asyncio.get_running_loop()
    mode_switcher._handle_sigterm()

    # Needs a small sleep to allow the create_task to execute
    await asyncio.sleep(0.01)
    mode_switcher._teardown_and_exit.assert_called_once()

@pytest.mark.asyncio
async def test_sigterm_handling_idle(mode_switcher, mock_app):
    mode_switcher._loop = asyncio.get_running_loop()
    mode_switcher._handle_sigterm()
    assert mock_app.exit_called is True

@pytest.mark.asyncio
async def test_sigint_handling(mode_switcher):
    mode_switcher._transition(ModeSwitcherState.SUSPENDING)
    mode_switcher._transition(ModeSwitcherState.RUNNING)
    mode_switcher._teardown_only = AsyncMock()

    mode_switcher._loop = asyncio.get_running_loop()
    mode_switcher._handle_sigint()

    # Needs a small sleep to allow the create_task to execute
    await asyncio.sleep(0.01)
    mode_switcher._teardown_only.assert_called_once()

@pytest.mark.asyncio
async def test_teardown_and_exit(mode_switcher, mock_app):
    mode_switcher._teardown_active_process = AsyncMock()
    mode_switcher.state = ModeSwitcherState.RUNNING

    async def change_state():
        await asyncio.sleep(0.1)
        mode_switcher.state = ModeSwitcherState.IDLE

    task = asyncio.create_task(change_state())
    await mode_switcher._teardown_and_exit()
    await task

    mode_switcher._teardown_active_process.assert_called_once()
    assert mock_app.exit_called is True

@pytest.mark.asyncio
async def test_teardown_only(mode_switcher):
    mode_switcher._teardown_active_process = AsyncMock()
    await mode_switcher._teardown_only()
    mode_switcher._teardown_active_process.assert_called_once()

def test_setup_signals_success(mock_app):
    # Test setting up signals normally
    with patch("asyncio.get_running_loop") as mock_loop_func:
        mock_loop = Mock()
        mock_loop_func.return_value = mock_loop
        switcher = ModeSwitcher(mock_app)

        mock_loop.add_signal_handler.assert_any_call(signal.SIGTERM, switcher._handle_sigterm)
        mock_loop.add_signal_handler.assert_any_call(signal.SIGINT, switcher._handle_sigint)

def test_setup_signals_exception(mock_app):
    # _setup_signals does try-except pass, so verify it handles exceptions
    with patch("asyncio.get_running_loop", side_effect=Exception("No loop")):
        # Should not raise
        switcher = ModeSwitcher(mock_app)
        assert switcher is not None

@pytest.mark.asyncio
async def test_teardown_process_break_early_on_term(mode_switcher):
    mock_process = Mock()
    mock_process.poll.side_effect = [None, 0, 0] # Need one extra 0 just in case it checks again
    mode_switcher.active_process = mock_process

    await mode_switcher._teardown_active_process()
    mock_process.terminate.assert_called_once()
    mock_process.kill.assert_not_called()

@pytest.mark.asyncio
async def test_teardown_process_break_early_on_kill(mode_switcher):
    mock_process = Mock()
    # 1 for initial check, 20 Nones for terminate loop
    # then 1 None for kill check, then 0 to break the kill loop early
    polls = [None] + [None] * 20 + [None, 0]
    mock_process.poll.side_effect = polls
    mode_switcher.active_process = mock_process

    with patch("asyncio.sleep", return_value=None):
        await mode_switcher._teardown_active_process()

    mock_process.terminate.assert_called_once()
    mock_process.kill.assert_called_once()

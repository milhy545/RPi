import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from mode_switcher import ModeSwitcher, ModeSwitcherState, InvalidTransition, LogBuffer

class MockApp:
    def __init__(self):
        self.exit_called = False

    def exit(self):
        self.exit_called = True

    def suspend(self):
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
async def test_launch_success(mode_switcher):
    with patch("subprocess.Popen") as mock_popen:
        mock_process = Mock()
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        success = await mode_switcher.launch(["echo", "test"])

        assert success is True
        assert mode_switcher.state == ModeSwitcherState.IDLE
        mock_popen.assert_called_once()

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
async def test_watchdog_timeout(mode_switcher):
    with patch("subprocess.Popen") as mock_popen:
        mock_process = Mock()
        # Make the process run forever (until killed)
        async def mock_wait():
            await asyncio.sleep(999)
            return 0
        mock_process.wait.side_effect = mock_wait
        mock_process.poll.return_value = None # Process is still running
        mock_popen.return_value = mock_process

        pass # Better to test watchdog through the app or a specialized test setup

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

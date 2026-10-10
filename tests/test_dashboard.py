import asyncio
import sys
import threading
import time
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mode_switcher import ModeSwitcher
from mode_switcher import ModeSwitcherState


class DashboardHarness:
    def __init__(self) -> None:
        self.exit_called = False
        self.pause_api_server_called = False
        self.resume_api_server_called = False
        self.replay_log_buffer_called = False
        self.mode_switcher = ModeSwitcher(self)

    def exit(self) -> None:
        self.exit_called = True

    def pause_api_server(self) -> None:
        self.pause_api_server_called = True

    def resume_api_server(self) -> None:
        self.resume_api_server_called = True

    def replay_log_buffer(self) -> None:
        self.replay_log_buffer_called = True

    def suspend(self):
        return nullcontext()

    def write_log(self, message: str) -> None:
        self.mode_switcher.log_buffer.write(message)


class FakeProcess:
    def __init__(self, return_code: int | None = 0, delay: float = 0.0) -> None:
        self.return_code = return_code
        self.delay = delay
        self._done = threading.Event()
        self._code: int | None = None

    def wait(self) -> int:
        if self.return_code is None:
            self._done.wait()
        elif self.delay:
            deadline = time.monotonic() + self.delay
            while time.monotonic() < deadline and not self._done.is_set():
                time.sleep(0.005)
            if self._code is None:
                self._code = self.return_code
                self._done.set()
        else:
            self._code = self.return_code
            self._done.set()
        return self._code if self._code is not None else -15

    def poll(self) -> int | None:
        return self._code if self._done.is_set() else None

    def terminate(self) -> None:
        self._code = -15
        self._done.set()

    def kill(self) -> None:
        self._code = -9
        self._done.set()


def fake_popen(command: list[str], **_kwargs) -> FakeProcess:
    if command[0] == "false":
        return FakeProcess(return_code=1)
    if command[:2] == ["sleep", "999"]:
        return FakeProcess(return_code=0, delay=5.0)
    if command[0] == "sleep":
        return FakeProcess(return_code=0, delay=float(command[1]))
    return FakeProcess(return_code=0)


async def wait_for_state(
    app: DashboardHarness,
    state: ModeSwitcherState,
    timeout: float = 2.0,
) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if app.mode_switcher.state == state:
            return
        await asyncio.sleep(0.02)
    raise AssertionError(f"State is {app.mode_switcher.state}, expected {state}")


async def wait_for_exit(app: DashboardHarness, timeout: float = 2.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if app.exit_called:
            return
        await asyncio.sleep(0.02)
    raise AssertionError("Dashboard exit was not requested")


async def run_tests() -> None:
    print("=== STARTING MODE SWITCHER TEST SUITE ===")
    app = DashboardHarness()

    assert app.mode_switcher.state == ModeSwitcherState.IDLE
    print("App started in IDLE mode")

    print("\n--- Testing Watchdog Timeout ---")
    watchdog_result = await app.mode_switcher.launch(["sleep", "999"], timeout=0.05)
    assert watchdog_result is False
    assert app.mode_switcher.state == ModeSwitcherState.IDLE
    assert any("Watchdog fired" in log for log in app.mode_switcher.log_buffer.get_lines())
    print("Watchdog fired, terminated process, and restored state to IDLE")

    print("\n--- Testing Crash Recovery ---")
    crash_result = await app.mode_switcher.launch(["false"], timeout=0)
    assert crash_result is False
    assert app.mode_switcher.state == ModeSwitcherState.IDLE
    assert any("returned code 1" in log for log in app.mode_switcher.log_buffer.get_lines())
    print("Crash recovery verified after non-zero exit")

    print("\n--- Testing Concurrency Serialization ---")
    t1 = asyncio.create_task(app.mode_switcher.launch(["sleep", "0.1"], timeout=0))
    await asyncio.sleep(0.02)
    t2 = asyncio.create_task(app.mode_switcher.launch(["sleep", "0.1"], timeout=0))
    assert await asyncio.gather(t1, t2) == [True, True]
    assert app.mode_switcher.state == ModeSwitcherState.IDLE
    print("Concurrency serialization works")

    print("\n--- Testing SIGINT Handling ---")
    sigint_task = asyncio.create_task(app.mode_switcher.launch(["sleep", "999"], timeout=0))
    await wait_for_state(app, ModeSwitcherState.RUNNING)
    app.mode_switcher._handle_sigint()
    assert await sigint_task is False
    assert app.mode_switcher.state == ModeSwitcherState.IDLE
    print("SIGINT handled, subprocess terminated, state restored to IDLE")

    print("\n--- Testing SIGTERM Handling ---")
    sigterm_task = asyncio.create_task(app.mode_switcher.launch(["sleep", "999"], timeout=0))
    await wait_for_state(app, ModeSwitcherState.RUNNING)
    app.mode_switcher._handle_sigterm()
    assert await sigterm_task is False
    assert app.mode_switcher.state == ModeSwitcherState.IDLE
    await wait_for_exit(app)
    print("SIGTERM handled, clean shutdown initiated")

    assert app.pause_api_server_called is True
    assert app.resume_api_server_called is True
    assert app.replay_log_buffer_called is True
    print("\n=== ALL TESTS PASSED SUCCESSFULLY ===")


def test_mode_switcher_suite() -> None:
    with patch("mode_switcher.subprocess.Popen", side_effect=fake_popen):
        asyncio.run(run_tests())


if __name__ == "__main__":
    test_mode_switcher_suite()

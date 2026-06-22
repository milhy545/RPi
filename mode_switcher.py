import asyncio
import subprocess
import signal
import sys
from enum import Enum, auto

# Timeout constants per mode
STEAMLINK_TIMEOUT = 0       # Unlimited
MPV_TIMEOUT = 0             # Unlimited
TEST_TIMEOUT = 30           # 30 seconds for test
SPOTIFY_TIMEOUT = 0         # Unlimited

class ModeSwitcherState(Enum):
    IDLE = auto()
    SUSPENDING = auto()
    RUNNING = auto()
    RESUMING = auto()

class InvalidTransition(Exception):
    pass

class LogBuffer:
    """Stores the last N log lines in memory to survive TUI suspension/resume."""
    def __init__(self, max_lines: int = 200):
        self.max_lines = max_lines
        self.lines = []

    def write(self, line: str):
        self.lines.append(line)
        if len(self.lines) > self.max_lines:
            self.lines.pop(0)

    def get_lines(self) -> list[str]:
        return list(self.lines)

    def clear(self):
        self.lines.clear()

class ModeSwitcher:
    def __init__(self, app):
        self.app = app
        self.state = ModeSwitcherState.IDLE
        self.lock = asyncio.Lock()
        self.log_buffer = LogBuffer()
        self.active_process = None
        self.watchdog_task = None
        self._teardown_requested = False
        self._loop = None
        self._setup_signals()

    def _setup_signals(self):
        try:
            loop = asyncio.get_running_loop()
            loop.add_signal_handler(signal.SIGTERM, self._handle_sigterm)
            loop.add_signal_handler(signal.SIGINT, self._handle_sigint)
        except Exception:
            pass

    def _transition(self, new_state: ModeSwitcherState):
        allowed = {
            ModeSwitcherState.IDLE: [ModeSwitcherState.SUSPENDING],
            ModeSwitcherState.SUSPENDING: [ModeSwitcherState.RUNNING, ModeSwitcherState.IDLE],
            ModeSwitcherState.RUNNING: [ModeSwitcherState.RESUMING],
            ModeSwitcherState.RESUMING: [ModeSwitcherState.IDLE],
        }
        if new_state not in allowed.get(self.state, []):
            self.log_buffer.write(f"[ERROR] Invalid transition: {self.state.name} -> {new_state.name}")
            raise InvalidTransition(f"Cannot transition from {self.state.name} to {new_state.name}")
        self.state = new_state

    async def launch(self, command: list[str], timeout: float = 0):
        # Concurrency guard: reject immediately if not in IDLE state
        if self.state != ModeSwitcherState.IDLE:
            self.log_buffer.write(f"[WARNING] Launch rejected: switcher is in state {self.state.name}")
            return False

        self._transition(ModeSwitcherState.SUSPENDING)

        async with self.lock:
            self.log_buffer.write(f"[SYSTEM] Suspending TUI. Executing: {' '.join(command)}")

            # Pause aiohttp API server requests
            if hasattr(self.app, "pause_api_server"):
                self.app.pause_api_server()

            loop = asyncio.get_running_loop()
            self._loop = loop
            self._teardown_requested = False
            exit_code = -1

            self._transition(ModeSwitcherState.RUNNING)
            if timeout > 0:
                self._start_watchdog(timeout)

            def run_sync():
                try:
                    # Execute synchronous command with inherited raw stdin/stdout/stderr
                    # to ensure interactive apps receive direct TTY access
                    self.active_process = subprocess.Popen(
                        command,
                        stdin=sys.__stdin__,
                        stdout=sys.__stdout__,
                        stderr=sys.__stderr__,
                    )
                    return self.active_process.wait()
                except Exception as e:
                    loop.call_soon_threadsafe(self.log_buffer.write, f"[ERROR] Subprocess exception: {e}")
                    return -1

            try:
                # Textual suspend context manager suspends TUI rendering.
                # If running in a headless test environment, this is not supported,
                # so we fall back to running without suspension.
                try:
                    with self.app.suspend():
                        exit_code = await loop.run_in_executor(None, run_sync)
                except Exception as e:
                    if "not supported in this environment" in str(e):
                        self.log_buffer.write("[SYSTEM] App.suspend not supported in this environment, running without suspension.")
                        exit_code = await loop.run_in_executor(None, run_sync)
                    else:
                        raise e
            except Exception as e:
                self.log_buffer.write(f"[ERROR] Suspension block execution failed: {e}")
                exit_code = -1
            finally:
                self._cancel_watchdog()
                self.active_process = None
                
                self._transition(ModeSwitcherState.RESUMING)
                self.log_buffer.write(f"[SYSTEM] Subprocess returned code {exit_code}")

                # Resume aiohttp API server requests
                if hasattr(self.app, "resume_api_server"):
                    self.app.resume_api_server()

                self._transition(ModeSwitcherState.IDLE)

                # Replay log buffer to ensure logs survive suspend/resume
                if hasattr(self.app, "replay_log_buffer"):
                    self.app.replay_log_buffer()

            return exit_code == 0

    async def _teardown_active_process(self):
        proc = self.active_process
        if proc and proc.poll() is None:
            self.log_buffer.write("[SYSTEM] Terminating active subprocess...")
            proc.terminate()
            # 2 seconds grace period
            for _ in range(20):
                if proc.poll() is not None:
                    break
                await asyncio.sleep(0.1)

            if proc.poll() is None:
                self.log_buffer.write("[SYSTEM] Subprocess did not terminate. Killing...")
                proc.kill()
                for _ in range(10):
                    if proc.poll() is not None:
                        break
                    await asyncio.sleep(0.1)

    def _handle_sigterm(self):
        if self._loop is None:
            if self.state == ModeSwitcherState.IDLE:
                self.app.exit()
            return

        if self._teardown_requested:
            return

        if self.state == ModeSwitcherState.RUNNING:
            self._teardown_requested = True
            self._loop.call_soon_threadsafe(
                lambda: asyncio.ensure_future(self._teardown_and_exit(), loop=self._loop)
            )
        elif self.state == ModeSwitcherState.IDLE:
            self.app.exit()

    def _handle_sigint(self):
        if self._loop is None:
            return

        if self._teardown_requested:
            return

        if self.state == ModeSwitcherState.RUNNING:
            self._teardown_requested = True
            self._loop.call_soon_threadsafe(
                lambda: asyncio.ensure_future(self._teardown_only(), loop=self._loop)
            )

    async def _teardown_and_exit(self):
        await self._teardown_active_process()
        while self.state == ModeSwitcherState.RUNNING:
            await asyncio.sleep(0.1)
        self.app.exit()

    async def _teardown_only(self):
        await self._teardown_active_process()

    def _start_watchdog(self, timeout: float):
        self.log_buffer.write(f"[SYSTEM] Watchdog armed: {timeout}s timeout")
        self.watchdog_task = asyncio.create_task(self._watchdog_timer(timeout))

    def _cancel_watchdog(self):
        if self.watchdog_task:
            self.watchdog_task.cancel()
            self.watchdog_task = None

    async def _watchdog_timer(self, timeout: float):
        try:
            await asyncio.sleep(timeout)
            self.log_buffer.write(f"[WARNING] Watchdog fired: subprocess exceeded {timeout}s limit")
            await self._teardown_active_process()
        except asyncio.CancelledError:
            pass

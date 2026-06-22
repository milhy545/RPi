"""Tests for fix_tui.py refactoring script."""

import os
import shutil
import subprocess
from pathlib import Path

# Realistic mock data matching the regexes in fix_tui.py
MOCK_TUI_CONTENT = """import time

class SystemStats:
    def on_mount(self) -> None:
        pass

INACTIVITY_TIMEOUT = 999999.0
class MatrixRain:
    def on_mount(self) -> None:
        pass

class MatrixRain:
    pass

class IdleScreen(Screen):
    pass

class RPiDashboard:
    def on_mount(self) -> None:
        pass

    async def handle_status(self):
        status = {
            "screensaver_active": isinstance(self.screen, IdleScreen),
            "other_status": True,
        }
        status2 = {
            "screensaver_active": False,
        }

    async def handle_system_screensaver(self):
        pass

    async def play_media(self):
        self.reset_inactivity()
        play_something()

    def reset_inactivity(self) -> None:
        self._check_settings_cache()
        pass

    def on_key(self):
        self.reset_inactivity()
        handle_key()

    def on_mouse_move(self, event) -> None:
        reset_mouse()

    async def run_watchdog_test(self):
        pass

    async def update_settings_data(self) -> None:
        self._updating_settings = True
        do_some_work()
        self._updating_settings = False

    def setup_api(self):
            api_app.router.add_post("/system/screensaver", _system_screensaver)

            async def _system_screensaver(req):
                return "ok"

            api_app.router.add_post("/other/route", _other_route)
"""

def get_fix_tui_source_path() -> str:
    """Get the absolute path to the fix_tui.py script.

    Returns:
        Absolute path to fix_tui.py as a string.
    """
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "fix_tui.py"
    )

def test_fix_tui_success(tmp_path: Path):
    """Test successful application of fix_tui.py script.

    Args:
        tmp_path: Pytest temporary path fixture.
    """
    tui_file = tmp_path / "tui.py"
    tui_file.write_text(MOCK_TUI_CONTENT)

    fix_tui_path = tmp_path / "fix_tui.py"
    shutil.copy(get_fix_tui_source_path(), fix_tui_path)

    subprocess.run(["python", "fix_tui.py"], cwd=tmp_path, check=True)

    content = tui_file.read_text()

    assert "INACTIVITY_TIMEOUT" not in content
    assert "class IdleScreen" not in content
    assert "screensaver_active" not in content
    assert "async def handle_system_screensaver" not in content
    assert "self.reset_inactivity()" not in content
    assert "def reset_inactivity(self)" not in content
    assert "def on_mouse_move" not in content
    assert 'self._settings_cache = {' in content
    assert 'self._settings_cache_ttl = 10.0' in content
    assert 'api_app.router.add_post("/system/screensaver"' not in content
    assert 'async def _system_screensaver(req)' not in content
    assert "class RPiDashboard:" in content
    assert "class SystemStats:" in content
    assert 'api_app.router.add_post("/other/route"' in content

def test_fix_tui_idempotency(tmp_path: Path):
    """Test that multiple runs of fix_tui.py yield the same result.

    Args:
        tmp_path: Pytest temporary path fixture.
    """
    tui_file = tmp_path / "tui.py"
    tui_file.write_text(MOCK_TUI_CONTENT)

    fix_tui_path = tmp_path / "fix_tui.py"
    shutil.copy(get_fix_tui_source_path(), fix_tui_path)

    subprocess.run(["python", "fix_tui.py"], cwd=tmp_path, check=True)
    content_after_first = tui_file.read_text()

    subprocess.run(["python", "fix_tui.py"], cwd=tmp_path, check=True)
    content_after_second = tui_file.read_text()

    assert content_after_first == content_after_second

def test_fix_tui_missing_file(tmp_path: Path):
    """Test failure mode when tui.py is missing.

    Args:
        tmp_path: Pytest temporary path fixture.
    """
    fix_tui_path = tmp_path / "fix_tui.py"
    shutil.copy(get_fix_tui_source_path(), fix_tui_path)

    result = subprocess.run(
        ["python", "fix_tui.py"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False
    )

    assert result.returncode != 0
    assert "FileNotFoundError" in result.stderr or "No such file" in result.stderr

def test_fix_tui_coverage_hack(monkeypatch, tmp_path):
    """Import fix_tui directly to allow coverage collection.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Pytest temporary path fixture.
    """
    tui_file = tmp_path / "tui.py"
    tui_file.write_text(MOCK_TUI_CONTENT)

    source_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(source_dir)

    # pylint: disable=unused-import, import-outside-toplevel, import-error
    import fix_tui # noqa: F401

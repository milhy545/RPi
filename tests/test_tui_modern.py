"""Test modern TUI module."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))



def test_import_modern_tui():
    """Test modern TUI import."""
    from rpi_dashboard.tui.modern import ModernDashboard, SystemStats, DeviceList, WiFiPanel, SettingsPanel
    assert ModernDashboard is not None
    assert SystemStats is not None
    assert DeviceList is not None
    assert WiFiPanel is not None
    assert SettingsPanel is not None


def test_tui_has_css():
    """Test that TUI has CSS defined."""
    from rpi_dashboard.tui.modern import ModernDashboard
    assert hasattr(ModernDashboard, 'CSS')
    assert len(ModernDashboard.CSS) > 0


def test_tui_has_bindings():
    """Test that TUI has keyboard bindings."""
    from rpi_dashboard.tui.modern import ModernDashboard
    assert hasattr(ModernDashboard, 'BINDINGS')
    assert len(ModernDashboard.BINDINGS) > 0


def test_system_stats_methods():
    """Test SystemStats has required methods."""
    from rpi_dashboard.tui.modern import SystemStats
    assert hasattr(SystemStats, 'get_cpu_usage')
    assert hasattr(SystemStats, 'get_ram_usage')
    assert hasattr(SystemStats, 'get_cpu_temp')
    assert hasattr(SystemStats, 'update_stats')


def test_live_tui_operational_tabs_have_usable_height():
    """The TV entrypoint still uses tui.py, so operational tabs must render."""

    async def run_check():
        import tui
        from textual.widgets import TabbedContent

        tui.API_PORT = 0
        app = tui.RPiDashboard()
        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause(0.2)
            tabs = app.query_one(TabbedContent)

            for tab_id, selector in (
                ("tab_audio", "#panel_audio"),
                ("tab_devices", "#panel_bluetooth"),
                ("tab_network", "#panel_network"),
                ("tab_network", "#panel_wifi"),
            ):
                tabs.active = tab_id
                await pilot.pause(0.1)
                panel = app.query_one(selector)
                assert panel.region.height >= 8
                assert panel.region.y >= 3

    asyncio.run(run_check())


def test_live_tui_uses_task_oriented_tabs():
    async def run_check():
        import tui
        from textual.widgets import TabbedContent, TabPane

        tui.API_PORT = 0
        app = tui.RPiDashboard()
        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause(0.2)
            tabs = app.query_one(TabbedContent)
            pane_ids = [pane.id for pane in app.query(TabPane)]
            assert pane_ids == [
                "tab_player",
                "tab_apps",
                "tab_audio",
                "tab_devices",
                "tab_network",
                "tab_system",
                "tab_logs",
            ]
            assert tabs.active == "tab_player"

    asyncio.run(run_check())

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


def test_live_tui_has_ascii_status_bar():
    async def run_check():
        import tui
        from textual.widgets import Static

        tui.API_PORT = 0
        app = tui.RPiDashboard()
        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause(0.5)
            status = app.query_one("#top_status", Static)
            rendered = str(status.render())
            assert "MODE:" in rendered
            assert "MODE: IDLE" in rendered
            assert "CPU:" in rendered
            assert "RAM:" in rendered
            assert all(ord(ch) < 128 for ch in rendered)

    asyncio.run(run_check())


def test_live_tui_defaults_to_czech_and_switches_to_english():
    async def run_check():
        import tui
        from textual.widgets import Button, Input, Static

        tui.API_PORT = 0
        app = tui.RPiDashboard()
        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause(0.2)
            assert str(app.query_one("#language_label", Static).render()).startswith("Jazyk:")
            assert str(app.query_one("#btn_mpv", Button).label) == "Spustit MPV"
            assert app.query_one("#input_mpv_url", Input).placeholder == "YouTube nebo prima URL..."

            await pilot.click("#btn_lang_en")
            await pilot.pause(0.1)
            assert str(app.query_one("#language_label", Static).render()).startswith("Language:")
            assert str(app.query_one("#btn_mpv", Button).label) == "Start MPV"
            assert app.query_one("#input_mpv_url", Input).placeholder == "YouTube or direct URL..."

    asyncio.run(run_check())


def test_system_stats_render_is_ascii():
    import tui

    stats = tui.SystemStats()
    stats.get_cpu_usage = lambda: 1.2
    stats.get_ram_usage = lambda: (0.4, 0.7)
    stats.get_cpu_temp = lambda: 42.0
    stats.get_local_ip = lambda: "127.0.0.1"
    stats.update_stats()
    rendered = str(stats.render())
    assert "CPU:" in rendered
    assert "TEMP:" in rendered
    assert all(ord(ch) < 128 for ch in rendered)


def test_live_tui_shows_return_hints():
    async def run_check():
        import tui
        from textual.widgets import Static, TabbedContent

        tui.API_PORT = 0
        app = tui.RPiDashboard()
        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause(0.2)
            player_hint = str(app.query_one("#hint_player_return", Static).render())
            assert "Zastavit vse" in player_hint

            app.query_one(TabbedContent).active = "tab_apps"
            await pilot.pause(0.1)
            apps_hint = str(app.query_one("#hint_apps_return", Static).render())
            assert "Ctrl-b" in apps_hint
            assert "potom d" in apps_hint

            await pilot.click("#btn_lang_en")
            await pilot.pause(0.1)
            apps_hint_en = str(app.query_one("#hint_apps_return", Static).render())
            assert "then d" in apps_hint_en

    asyncio.run(run_check())


def test_audio_tab_uses_human_sink_labels(monkeypatch):
    async def run_check():
        import tui
        from textual.widgets import OptionList, TabbedContent

        async def fake_run_sys_cmd(self, cmd, timeout=5.0):
            if cmd == "pactl get-default-sink":
                return "alsa_output.platform-3f902000.hdmi.hdmi-stereo"
            if cmd == "pactl list short sinks":
                return (
                    "0\talsa_output.platform-3f902000.hdmi.hdmi-stereo\tPipeWire\n"
                    "1\tbluez_sink.24_4B_03_92_0B_8C.a2dp_sink\tPipeWire"
                )
            return ""

        monkeypatch.setattr(tui.RPiDashboard, "run_sys_cmd", fake_run_sys_cmd)
        tui.API_PORT = 0
        app = tui.RPiDashboard()
        async with app.run_test(size=(120, 35)) as pilot:
            app.query_one(TabbedContent).active = "tab_audio"
            await app.update_audio_sinks()
            await pilot.pause(0.1)
            sink_list = app.query_one("#list_audio_sinks", OptionList)
            prompts = [
                str(sink_list.get_option_at_index(i).prompt)
                for i in range(sink_list.option_count)
            ]
            assert any("TV HDMI" in prompt and "[ACTIVE]" in prompt for prompt in prompts)
            assert any("Bluetooth Audio" in prompt for prompt in prompts)

    asyncio.run(run_check())


def test_devices_tab_shows_bluetooth_status_rows(monkeypatch):
    async def run_check():
        import tui
        from textual.widgets import OptionList, TabbedContent

        async def fake_run_sys_cmd(self, cmd, timeout=5.0):
            if cmd == "bluetoothctl devices Paired":
                return (
                    "Device 24:4B:03:92:0B:8C [Samsung] Soundbar J-Series\n"
                    "Device 5C:BA:37:01:74:E9 Xbox Wireless Controller"
                )
            if cmd == "bluetoothctl devices Connected":
                return "Device 24:4B:03:92:0B:8C [Samsung] Soundbar J-Series"
            return ""

        monkeypatch.setattr(tui.RPiDashboard, "run_sys_cmd", fake_run_sys_cmd)
        tui.API_PORT = 0
        app = tui.RPiDashboard()
        async with app.run_test(size=(120, 35)) as pilot:
            app.query_one(TabbedContent).active = "tab_devices"
            await app.update_bluetooth_devices()
            await pilot.pause(0.1)
            bt_list = app.query_one("#list_bluetooth_devices", OptionList)
            prompts = [str(bt_list.get_option_at_index(i).prompt) for i in range(bt_list.option_count)]
            assert any("[CONNECTED] [Samsung] Soundbar J-Series" in prompt for prompt in prompts)
            assert any("[PAIRED] Xbox Wireless Controller" in prompt for prompt in prompts)

    asyncio.run(run_check())


def test_wifi_empty_state_is_explanatory(monkeypatch):
    async def run_check():
        import tui
        from textual.widgets import OptionList

        async def fake_run_sys_cmd(self, cmd, timeout=5.0):
            return ""

        monkeypatch.setattr(tui.RPiDashboard, "run_sys_cmd", fake_run_sys_cmd)
        tui.API_PORT = 0
        app = tui.RPiDashboard()
        async with app.run_test(size=(120, 35)):
            await app.scan_wifi()
            wifi_list = app.query_one("#list_wifi_networks", OptionList)
            assert str(wifi_list.get_option_at_index(0).prompt) == (
                "Zadne Wi-Fi site nenalezeny. Spust sken znovu nebo zkontroluj adapter."
            )
            app.language = "en"
            app.apply_language()
            assert str(wifi_list.get_option_at_index(0).prompt) == (
                "No Wi-Fi networks found. Run scan again or check adapter."
            )

    asyncio.run(run_check())

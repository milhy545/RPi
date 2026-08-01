import pytest
from textual.widgets import TabbedContent, TabPane
from tui import RPiDashboard

@pytest.mark.asyncio
async def test_tui_terminal_tab_exists():
    app = RPiDashboard()
    async with app.run_test() as pilot:
        tabs = app.query_one(TabbedContent)
        tab_ids = [pane.id for pane in tabs.query(TabPane)]
        assert "tab_terminal" in tab_ids
        
        # Select terminal tab
        tabs.active = "tab_terminal"
        await pilot.pause()
        
        # Check locked message
        locked_msg = app.query_one("#txt_terminal_locked")
        assert "Terminal access is only available via WebUI or SSH" in str(locked_msg.render())

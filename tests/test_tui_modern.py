"""Test modern TUI module."""

import pytest


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

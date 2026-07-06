"""Test that all service modules can be imported."""

import pytest


def test_import_audio():
    """Test audio module import."""
    from rpi_dashboard.services import audio
    assert hasattr(audio, 'audio_state')
    assert hasattr(audio, 'get_audio_matrix')
    assert hasattr(audio, 'audio_set_volume')


def test_import_player():
    """Test player module import."""
    from rpi_dashboard.services import player
    assert hasattr(player, 'mpv_start')
    assert hasattr(player, 'mpv_stop')
    assert hasattr(player, 'mpv_st')


def test_import_devices():
    """Test devices module import."""
    from rpi_dashboard.services import devices
    assert hasattr(devices, 'devices_state')
    assert hasattr(devices, 'bluetooth_scan_devices')
    assert hasattr(devices, 'wifi_status')


def test_import_cec():
    """Test CEC module import."""
    from rpi_dashboard.services import cec
    assert hasattr(cec, 'cec_scan')
    assert hasattr(cec, 'cec_power_on')
    assert hasattr(cec, 'cec_volume_up')


def test_import_system():
    """Test system module import."""
    from rpi_dashboard.services import system
    assert hasattr(system, 'get_system_stats')
    assert hasattr(system, 'restart_mpv')
    assert hasattr(system, 'restart_dashboard')


def test_import_terminal():
    """Test terminal module import."""
    from rpi_dashboard.services import terminal
    assert hasattr(terminal, 'terminal_connect')
    assert hasattr(terminal, 'terminal_disconnect')


def test_import_api_routes():
    """Test API routes import."""
    from rpi_dashboard.api import routes
    assert hasattr(routes, 'ROUTES')
    assert hasattr(routes, 'get_route')
    assert len(routes.ROUTES) > 0


def test_import_api_handlers():
    """Test API handlers import."""
    from rpi_dashboard.api import handlers
    assert hasattr(handlers, 'handle_audio_state')
    assert hasattr(handlers, 'handle_mpv_play')
    assert hasattr(handlers, 'handle_devices_state')


def test_import_models():
    """Test models import."""
    from rpi_dashboard.models import schemas
    assert hasattr(schemas, 'ApiResponse')
    assert hasattr(schemas, 'AudioState')
    assert hasattr(schemas, 'MpvStatus')

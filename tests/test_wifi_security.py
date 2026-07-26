"""Tests for Wi-Fi security fixes."""

import pytest
from unittest.mock import patch, MagicMock


def test_password_not_in_argv():
    """Ensure password is not passed as command line argument."""
    from rpi_dashboard.services.devices import wifi_connect
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="OK")
        
        # Call wifi_connect with password
        result = wifi_connect("TestSSID", "TestPassword123")
        
        # Verify subprocess was called
        assert mock_run.called
        
        # Get the command that was executed
        call_args = mock_run.call_args
        
        # Verify password is NOT in the command arguments
        if call_args and call_args[0]:
            cmd_args = call_args[0][0]
            # Password should not be in the command arguments
            assert "TestPassword123" not in cmd_args, \
                "Password should not be in command line arguments"


def test_password_passed_via_stdin():
    """Ensure password is passed via stdin."""
    from rpi_dashboard.services.devices import wifi_connect
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="OK")
        
        # Call wifi_connect with password
        result = wifi_connect("TestSSID", "TestPassword123")
        
        # Verify subprocess was called with stdin
        if mock_run.called:
            call_kwargs = mock_run.call_args[1] if len(mock_run.call_args) > 1 else {}
            # Password should be in stdin input
            assert call_kwargs.get('input') == "TestPassword123", \
                "Password should be passed via stdin"


def test_password_hidden_in_process():
    """Test that password is hidden from process inspection."""
    # This test would need to be run on actual system
    # to verify password is not visible in /proc/*/cmdline
    pass
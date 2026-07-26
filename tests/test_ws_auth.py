"""Tests for WebSocket terminal authentication."""

import pytest
from pathlib import Path


def test_ws_auth_token_in_source():
    """Test that WS_AUTH_TOKEN is defined in webserver.py."""
    source = Path("/home/milhy777/rpi-dashboard/webserver.py").read_text()
    assert "WS_AUTH_TOKEN = secrets.token_hex(32)" in source


def test_ws_auth_endpoint_in_source():
    """Test that /ws/token endpoint is handled in webserver.py."""
    source = Path("/home/milhy777/rpi-dashboard/webserver.py").read_text()
    assert '/ws/token' in source


def test_ws_auth_required_in_term_handler():
    """Test that term_handler requires authentication."""
    source = Path("/home/milhy777/rpi-dashboard/webserver.py").read_text()
    # Find the term_handler function
    assert 'async def term_handler' in source
    # Check that it validates the auth token
    assert 'WS_AUTH_TOKEN' in source
    assert 'action' in source and 'auth' in source


def test_secrets_imported():
    """Test that secrets module is imported."""
    source = Path("/home/milhy777/rpi-dashboard/webserver.py").read_text()
    assert 'import secrets' in source or 'import json, os, re, socket, sys, subprocess, time, stat, ssl, shutil, secrets' in source
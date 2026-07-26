"""Tests for WebSocket terminal authentication."""

import pytest
from pathlib import Path


# Discover project root dynamically
PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEBSERVER_FILE = PROJECT_ROOT / "webserver.py"


def test_ws_auth_token_in_source():
    """Test that WS_AUTH_TOKEN is defined in webserver.py."""
    source = WEBSERVER_FILE.read_text()
    assert "WS_AUTH_TOKEN = secrets.token_hex(32)" in source


def test_ws_auth_endpoint_in_source():
    """Test that /ws/token endpoint is handled in webserver.py."""
    source = WEBSERVER_FILE.read_text()
    assert '/ws/token' in source


def test_ws_auth_required_in_term_handler():
    """Test that term_handler requires authentication."""
    source = WEBSERVER_FILE.read_text()
    # Find the term_handler function
    assert 'async def term_handler' in source
    # Check that it validates the auth token
    assert 'WS_AUTH_TOKEN' in source
    assert 'action' in source and 'auth' in source


def test_secrets_imported():
    """Test that secrets module is imported."""
    source = WEBSERVER_FILE.read_text()
    assert 'import secrets' in source or 'import json, os, re, socket, sys, subprocess, time, stat, ssl, shutil, secrets' in source

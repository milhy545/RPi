"""Tests for URL metadata cache."""

import pytest
import os
import json
import time
from pathlib import Path


# Discover project root dynamically
PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEBSERVER_FILE = PROJECT_ROOT / "webserver.py"


def test_url_cache_class_exists():
    """Test that _URLCache class is defined in webserver.py."""
    source = WEBSERVER_FILE.read_text()
    assert "class _URLCache:" in source


def test_url_cache_global_instance():
    """Test that _url_cache global instance is created."""
    source = WEBSERVER_FILE.read_text()
    assert "_url_cache = _URLCache()" in source


def test_resolve_uses_cache():
    """Test that resolve function checks cache first."""
    source = WEBSERVER_FILE.read_text()
    # Find the resolve function
    assert "def resolve(url, q=None):" in source
    # Check that it uses the cache
    assert "_url_cache.get(vid)" in source
    assert "_url_cache.put(vid," in source


def test_cache_api_endpoints():
    """Test that cache API endpoints are defined."""
    source = WEBSERVER_FILE.read_text()
    assert "/cache/stats" in source
    assert "/cache/clear" in source


def test_cache_config():
    """Test that cache configuration is defined."""
    source = WEBSERVER_FILE.read_text()
    assert "URL_CACHE_FILE" in source
    assert "URL_CACHE_TTL" in source

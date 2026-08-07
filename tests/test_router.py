from unittest.mock import patch

from router import route

def dummy_handler(self, q):
    pass

def test_route_existing_path():
    """Test that route returns the correct handler for an existing path."""
    mock_table = {"/test/path": dummy_handler}
    with patch.dict("handlers.route_table", mock_table, clear=True):
        assert route("/test/path") is dummy_handler

def test_route_non_existing_path():
    """Test that route returns None for a non-existing path."""
    mock_table = {"/test/path": dummy_handler}
    with patch.dict("handlers.route_table", mock_table, clear=True):
        assert route("/non/existing") is None

def test_route_empty_table():
    """Test that route returns None when the route table is completely empty."""
    with patch.dict("handlers.route_table", {}, clear=True):
        assert route("/any/path") is None

def test_route_with_query_string():
    """Test edge-case that providing a path with a query string returns None if not exactly matched."""
    mock_table = {"/test/path": dummy_handler}
    with patch.dict("handlers.route_table", mock_table, clear=True):
        assert route("/test/path?query=1") is None

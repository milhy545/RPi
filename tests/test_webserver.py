import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from webserver import norm, yt_id

@pytest.mark.parametrize("input_url, expected", [
    # Happy paths: normalizer removes redundant slashes in path
    ("http://example.com//test//path", "http://example.com/test/path"),
    ("https://example.com/test///path//", "https://example.com/test/path/"),
    ("http://example.com", "http://example.com"),
    ("https://example.com/normal/path", "https://example.com/normal/path"),

    # URL with query and fragment
    ("http://example.com//path?query=1#frag", "http://example.com/path?query=1#frag"),

    # Strip spaces
    ("  http://example.com//test  ", "http://example.com/test"),

    # Non HTTP/HTTPS schemes (should strip but NOT normalize slashes)
    ("ftp://example.com//test//path", "ftp://example.com//test//path"),
    ("file:///home//user//test", "file:///home//user//test"),

    # Malformed strings (should fallback to returning stripped string)
    ("just a random string", "just a random string"),
    ("http://[invalid-ipv6]//path", "http://[invalid-ipv6]//path"),

    # Non-string inputs (should safely return empty string)
    (None, ""),
    (123, ""),
    (3.14, ""),
    (["http://example.com"], ""),
    ({"url": "http://example.com"}, "")
])
def test_norm(input_url, expected):
    """Test the norm function for URL normalization and type safety."""
    assert norm(input_url) == expected

def test_yt_id_standard_url():
    assert yt_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert yt_id("http://youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

def test_yt_id_short_url():
    assert yt_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert yt_id("http://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

def test_yt_id_shorts_url():
    assert yt_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

def test_yt_id_embed_url():
    assert yt_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

def test_yt_id_with_extra_params():
    assert yt_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s") == "dQw4w9WgXcQ"
    assert yt_id("https://www.youtube.com/watch?feature=youtu.be&v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

def test_yt_id_invalid_urls():
    assert yt_id("https://www.google.com") == ""
    assert yt_id("not a url at all") == ""
    assert yt_id("https://youtube.com/watch?v=") == ""  # Too short ID, won't match regex exactly
    assert yt_id("") == ""

def test_yt_id_with_whitespace():
    # `norm` is used inside `yt_id`, which does `u.strip()`
    assert yt_id("  https://youtu.be/dQw4w9WgXcQ  ") == "dQw4w9WgXcQ"


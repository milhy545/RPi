import pytest
from webserver import yt_id

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

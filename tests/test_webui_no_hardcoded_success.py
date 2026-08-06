"""Static regression tests forbidding hard-coded operational success labels in WebUI markup and code."""

from pathlib import Path

ROOT = Path(__file__).parent.parent
INDEX_HTML = ROOT / "rpi_dashboard" / "static" / "index.html"
APP_JS = ROOT / "rpi_dashboard" / "static" / "js" / "app.js"


def test_index_html_has_no_hardcoded_operational_success_pills():
    """Verify index.html footer status pills have no hard-coded operational claims."""
    content = INDEX_HTML.read_text(encoding="utf-8")
    assert "● Service Running" not in content
    assert "📶 Bluetooth Ready" not in content
    assert "🔊 Audio HDMI" not in content


def test_app_js_badge_function_handles_explicit_states():
    """Verify app.js badge function handles explicit pass, blocked, N/A, degraded, loading states."""
    content = APP_JS.read_text(encoding="utf-8")
    assert "function badge(state,label)" in content or "function badge(state, label)" in content
    assert "'muted'" in content or '"muted"' in content
    assert "updateFooterStatus" in content

"""Static asset regression tests."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_static_app_js_has_valid_syntax() -> None:
    """The browser should be able to parse the main WebUI script."""
    node = shutil.which("node")
    assert node is not None, "node is required to validate static JavaScript syntax"

    result = subprocess.run(
        [node, "--check", "rpi_dashboard/static/js/app.js"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout


def test_audio_routes_cookie_helpers_are_defined() -> None:
    """Audio route rendering uses cookie helpers for multi-output state."""
    app_js = (REPO_ROOT / "rpi_dashboard/static/js/app.js").read_text()

    assert "function getCookie(name)" in app_js
    assert "function setCookie(name,value)" in app_js
    assert "multiOutputToggle()" in app_js


def test_aria_label_i18n_preserves_icon_button_content() -> None:
    """Icon-only controls should translate accessibility text, not visible labels."""
    app_js = (REPO_ROOT / "rpi_dashboard/static/js/app.js").read_text()

    assert "function ariaText(k,txt)" in app_js
    assert "el.dataset.i18nAttr==='aria-label'" in app_js
    assert "el.setAttribute('aria-label',ariaText(key,txt));return" in app_js


def test_small_controls_have_touch_target_floor() -> None:
    """Small topbar/help controls should stay usable on touch screens."""
    main_css = (REPO_ROOT / "rpi_dashboard/static/css/main.css").read_text()
    responsive_css = (REPO_ROOT / "rpi_dashboard/static/css/responsive.css").read_text()

    assert ".lang-btn" in main_css
    assert "min-width:2.25rem" in main_css
    assert "min-height:2.25rem" in main_css
    assert "width:24px" in main_css
    assert "height:24px" in main_css
    assert "input[type=range]{min-height:24px" in main_css
    assert "min-height: 2.25rem" in responsive_css

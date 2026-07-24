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
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=60,
        check=False,
    )

    assert result.returncode == 0


def test_audio_multi_output_uses_real_backend_state() -> None:
    """Multi-output must use the shared Audio API, not a cookie-only toggle."""
    app_js = (REPO_ROOT / "rpi_dashboard/static/js/app.js").read_text()

    assert "function getCookie(name)" in app_js
    assert "function setCookie(name,value)" in app_js
    assert "multiOutputToggle()" in app_js
    assert "api('/audio/multi-output?action=status')" in app_js
    assert "api('/audio/multi-output?action='+action)" in app_js
    assert "function multiOutputToggle(){let on=getCookie" not in app_js


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


def test_bluetooth_webui_uses_gemini_control_center_shell() -> None:
    """The production Bluetooth tab should keep the saved Gemini design shape."""
    index_html = (REPO_ROOT / "rpi_dashboard/static/index.html").read_text()
    main_css = (REPO_ROOT / "rpi_dashboard/static/css/main.css").read_text()
    app_js = (REPO_ROOT / "rpi_dashboard/static/js/app.js").read_text()

    assert 'id="bt-app" class="bt-app mode-advanced bt-theme-dark"' in index_html
    assert 'id="bt-topo-wrapper"' in index_html
    assert 'id="bt-topology-lines"' in index_html
    assert 'id="bt-filter-connected"' in index_html
    assert 'id="bt-device-details"' in index_html
    assert ".bt-sidebar-left" in main_css
    assert ".bt-sidebar-right" in main_css
    assert ".bt-topo-canvas" in main_css
    assert "function btDrawTopologyLines()" in app_js
    assert "function btInitInteractions()" in app_js
    assert "function btSelectedAction(action)" in app_js


def test_bluetooth_webui_production_tab_does_not_depend_on_external_cdn() -> None:
    """The integrated tab must be local static UI, not the standalone prototype."""
    index_html = (REPO_ROOT / "rpi_dashboard/static/index.html").read_text()

    assert "cdn.tailwindcss.com" not in index_html
    assert "unpkg.com/@phosphor-icons" not in index_html


def test_bluetooth_controls_call_real_settings_endpoints_and_confirm_destructive_actions() -> None:
    app_js = (REPO_ROOT / "rpi_dashboard/static/js/app.js").read_text()

    assert "'/bt/settings?auto_connect='" in app_js
    assert "'/bt/discoverable?adapter_id='" in app_js
    assert "if(action==='pair')return btStartPairing" in app_js
    assert "Start pairing with this device on the selected adapter?" in app_js
    assert "if(action==='remove'&&!confirm" in app_js
    assert "onoff==='off'&&!confirm" in app_js
    assert "Auto Connect '+(on?'enabled':'disabled'),'info'" not in app_js

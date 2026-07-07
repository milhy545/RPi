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

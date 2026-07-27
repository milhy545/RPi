"""Tests for environment-driven config overrides."""

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ws_port_reads_environment_override() -> None:
    env = os.environ.copy()
    env["RPIDASHBOARD_WS_PORT"] = "19098"

    result = subprocess.run(
        [sys.executable, "-c", "import config; print(config.WS_PORT)"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == "19098"

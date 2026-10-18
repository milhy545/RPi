from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess


RUN_CI_SCRIPT = Path(__file__).parents[1] / "tools" / "run-ci.sh"


def test_run_ci_rejects_unknown_profile_before_creating_report(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    tools = repo / "tools"
    tools.mkdir(parents=True)
    shutil.copy2(RUN_CI_SCRIPT, tools / "run-ci.sh")
    report_dir = tmp_path / "reports"
    env = os.environ.copy()
    env.update({"CI_PROFILE": "github-sfae", "REPORT_DIR": str(report_dir)})

    result = subprocess.run(
        ["bash", str(tools / "run-ci.sh")],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "unknown CI profile 'github-sfae'" in result.stderr
    assert not report_dir.exists()

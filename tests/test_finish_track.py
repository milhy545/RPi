from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest


SOURCE_SCRIPT = Path(__file__).parents[1] / "tools" / "finish-track.sh"


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


@pytest.fixture
def repo_factory(tmp_path: Path):
    def create(branch: str = "feature/test") -> tuple[Path, str]:
        repo = tmp_path / branch.replace("/", "-")
        repo.mkdir()
        _git(repo, "init", "--initial-branch", branch)
        _git(repo, "config", "user.name", "CI Test")
        _git(repo, "config", "user.email", "ci@example.invalid")

        tools = repo / "tools"
        tools.mkdir()
        shutil.copy2(SOURCE_SCRIPT, tools / "finish-track.sh")
        runner = tools / "run-ci.sh"
        runner.write_text(
            "#!/usr/bin/env bash\n"
            "set -e\n"
            "printf '%s %s\\n' \"$(git rev-parse HEAD)\" \"$CI_PROFILE\" >> \"$FAKE_CI_LOG\"\n"
            "exit \"${FAKE_CI_STATUS:-0}\"\n"
        )
        runner.chmod(0o755)
        (repo / "source.txt").write_text("base\n")
        _git(repo, "add", "source.txt", "tools")
        _git(repo, "commit", "-m", "initial")
        base_sha = _git(repo, "rev-parse", "HEAD")

        (repo / "source.txt").write_text("changed\n")
        return repo, base_sha

    return create


def _run(repo: Path, log: Path, *args: str, **extra_env: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "CI_PROFILE": "github-safe",
            "FAKE_CI_LOG": str(log),
            **extra_env,
        }
    )
    return subprocess.run(
        ["bash", str(repo / "tools" / "finish-track.sh"), *args],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
    )


def test_finish_track_runs_ci_before_commit_and_keeps_snapshot(repo_factory, tmp_path: Path) -> None:
    repo, base_sha = repo_factory()
    ci_log = tmp_path / "ci.log"

    result = _run(repo, ci_log, "fix: keep candidate commit safe")

    assert result.returncode == 0, result.stderr
    assert ci_log.read_text().strip() == f"{base_sha} github-safe"
    assert _git(repo, "log", "-1", "--format=%s") == "fix: keep candidate commit safe"
    assert _git(repo, "rev-parse", "HEAD^1") == base_sha
    assert _git(repo, "status", "--porcelain") == ""
    assert "pre-finish-track-" in _git(repo, "stash", "list")
    assert "PR CI and an exact-main GitHub Actions receipt" in result.stdout


def test_finish_track_does_not_commit_when_ci_fails(repo_factory, tmp_path: Path) -> None:
    repo, base_sha = repo_factory()
    ci_log = tmp_path / "ci.log"

    result = _run(repo, ci_log, "fix: failing validation", FAKE_CI_STATUS="1")

    assert result.returncode != 0
    assert _git(repo, "rev-parse", "HEAD") == base_sha
    assert (repo / "source.txt").read_text() == "changed\n"
    assert "no commit was created" in result.stderr
    assert ci_log.read_text().strip() == f"{base_sha} github-safe"


def test_finish_track_refuses_main(repo_factory, tmp_path: Path) -> None:
    repo, base_sha = repo_factory("main")
    ci_log = tmp_path / "ci.log"

    result = _run(repo, ci_log, "fix: no direct main commits")

    assert result.returncode != 0
    assert _git(repo, "rev-parse", "HEAD") == base_sha
    assert not ci_log.exists()
    assert "will not create commits directly on main" in result.stderr


def test_finish_track_rejects_runtime_reports(repo_factory, tmp_path: Path) -> None:
    repo, base_sha = repo_factory()
    ci_log = tmp_path / "ci.log"
    runtime_report = repo / "conductor" / "ci" / "reports" / "generated.md"
    runtime_report.parent.mkdir(parents=True)
    runtime_report.write_text("generated\n")

    result = _run(repo, ci_log, "fix: do not commit runtime data")

    assert result.returncode != 0
    assert _git(repo, "rev-parse", "HEAD") == base_sha
    assert "conductor/ci/reports/generated.md" in result.stderr


def test_finish_track_requires_a_commit_message(repo_factory, tmp_path: Path) -> None:
    repo, base_sha = repo_factory()

    result = _run(repo, tmp_path / "ci.log")

    assert result.returncode == 2
    assert _git(repo, "rev-parse", "HEAD") == base_sha
    assert "Usage:" in result.stderr


def test_finish_track_rejects_unknown_profile_before_snapshot(repo_factory, tmp_path: Path) -> None:
    repo, base_sha = repo_factory()
    ci_log = tmp_path / "ci.log"

    result = _run(
        repo,
        ci_log,
        "fix: reject unknown profile",
        CI_PROFILE="github-sfae",
    )

    assert result.returncode == 2
    assert _git(repo, "rev-parse", "HEAD") == base_sha
    assert not ci_log.exists()
    assert "pre-finish-track-" not in _git(repo, "stash", "list")
    assert "unsupported CI profile" in result.stderr

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess


SOURCE_ROOT = Path(__file__).parents[1]


def _verified_repo(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init", "--initial-branch", "feature/receipt-check", str(repo)],
        check=True,
        capture_output=True,
        text=True,
    )
    for key, value in (("user.name", "CI Test"), ("user.email", "ci@example.invalid")):
        subprocess.run(["git", "-C", str(repo), "config", key, value], check=True)
    tools = repo / "tools"
    tools.mkdir()
    for name in ("verify-done.sh", "receipt_lookup.py", "import_main_receipt.py"):
        shutil.copy2(SOURCE_ROOT / "tools" / name, tools / name)
    (repo / "source.txt").write_text("verified\n")
    subprocess.run(["git", "-C", str(repo), "add", "source.txt", "tools"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "fixture"], check=True)
    sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    tree = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD^{tree}"], text=True).strip()

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_ssh = fake_bin / "ssh"
    fake_ssh.write_text("#!/usr/bin/env sh\nexit 255\n")
    fake_ssh.chmod(0o755)
    fake_gh = fake_bin / "gh"
    fake_gh.write_text("#!/usr/bin/env sh\nprintf '%s\\n' '{\"workflow_runs\": []}'\n")
    fake_gh.chmod(0o755)
    return repo, sha, tree


def _run_verify(
    repo: Path,
    tmp_path: Path,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "RECEIPT_DIR": str(tmp_path / "receipts"),
            "REPORT_DIR": str(tmp_path / "reports"),
            "MILHY_PC_HOST": "unreachable-test-host",
            "PATH": f"{tmp_path / 'bin'}{os.pathsep}{env['PATH']}",
        }
    )
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(repo / "tools" / "verify-done.sh")],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
    )


def test_verify_done_fails_explicitly_when_receipt_is_missing(tmp_path: Path) -> None:
    repo, _, _ = _verified_repo(tmp_path)

    result = _run_verify(repo, tmp_path)

    assert result.returncode == 1
    assert "No receipt found for HEAD=" in result.stderr


def test_verify_done_accepts_matching_receipt_with_report_and_actions_url(tmp_path: Path) -> None:
    repo, sha, tree = _verified_repo(tmp_path)
    receipt_dir = tmp_path / "receipts"
    report_dir = tmp_path / "reports"
    receipt_dir.mkdir()
    report_dir.mkdir()
    report = report_dir / "pass.md"
    report.write_text("PASS\nexact commit verification\n")
    (receipt_dir / "matching.json").write_text(
        json.dumps(
            {
                "status": "done",
                "commit_sha": sha,
                "tree_hash": tree,
                "ci_report": str(report),
                "actions_url": "https://github.com/example/repo/actions/runs/1",
            }
        )
    )

    result = _run_verify(repo, tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "VERIFY-DONE: PASS" in result.stdout


def test_verify_done_accepts_detached_checkout_with_local_receipt(tmp_path: Path) -> None:
    repo, sha, tree = _verified_repo(tmp_path)
    subprocess.run(
        ["git", "-C", str(repo), "remote", "add", "origin", "https://github.com/example/repo.git"],
        check=True,
    )
    subprocess.run(["git", "-C", str(repo), "checkout", "--detach"], check=True, capture_output=True)

    receipt_dir = tmp_path / "receipts"
    report_dir = tmp_path / "reports"
    receipt_dir.mkdir()
    report_dir.mkdir()
    report = report_dir / "pass.md"
    report.write_text("PASS\ndetached CI checkout\n")
    (receipt_dir / "matching.json").write_text(
        json.dumps(
            {
                "status": "done",
                "commit_sha": sha,
                "tree_hash": tree,
                "ci_report": str(report),
                "actions_url": "https://github.com/example/repo/actions/runs/1",
            }
        )
    )

    result = _run_verify(repo, tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Detached checkout; exact ref identity was checked by the caller" in result.stdout


def test_verify_done_rejects_pr_receipt_for_main_push(tmp_path: Path) -> None:
    repo, sha, tree = _verified_repo(tmp_path)
    subprocess.run(
        ["git", "-C", str(repo), "remote", "add", "origin", "https://github.com/example/repo.git"],
        check=True,
    )
    subprocess.run(["git", "-C", str(repo), "checkout", "--detach"], check=True, capture_output=True)

    receipt_dir = tmp_path / "receipts"
    report_dir = tmp_path / "reports"
    receipt_dir.mkdir()
    report_dir.mkdir()
    report = report_dir / "pass.md"
    report.write_text("PASS\nPR receipt\n")
    (receipt_dir / "pull-request.json").write_text(
        json.dumps(
            {
                "status": "done",
                "commit_sha": sha,
                "tree_hash": tree,
                "source": "github-actions-pull-request",
                "ci_report": str(report),
                "actions_url": "https://github.com/example/repo/actions/runs/1",
            }
        )
    )

    result = _run_verify(
        repo,
        tmp_path,
        {
            "GITHUB_ACTIONS": "true",
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_REF": "refs/heads/main",
        },
    )

    assert result.returncode == 1
    assert "No receipt found for HEAD=" in result.stderr


def test_verify_done_scans_runtime_artifacts_across_pr_range(tmp_path: Path) -> None:
    repo, base_sha, _ = _verified_repo(tmp_path)
    runtime_report = repo / "conductor" / "ci" / "reports" / "generated.md"
    runtime_report.parent.mkdir(parents=True)
    runtime_report.write_text("runtime artifact\n")
    subprocess.run(["git", "-C", str(repo), "add", "conductor/ci/reports/generated.md"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "add runtime artifact"],
        check=True,
        capture_output=True,
    )
    (repo / "later-change.txt").write_text("later commit\n")
    subprocess.run(["git", "-C", str(repo), "add", "later-change.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "add later change"],
        check=True,
        capture_output=True,
    )
    sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    tree = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD^{tree}"], text=True).strip()

    receipt_dir = tmp_path / "receipts"
    report_dir = tmp_path / "reports"
    receipt_dir.mkdir()
    report_dir.mkdir()
    report = report_dir / "pass.md"
    report.write_text("PASS\nrange verification\n")
    (receipt_dir / "matching.json").write_text(
        json.dumps(
            {
                "status": "done",
                "commit_sha": sha,
                "tree_hash": tree,
                "ci_report": str(report),
                "actions_url": "https://github.com/example/repo/actions/runs/1",
            }
        )
    )

    result = _run_verify(repo, tmp_path, {"VERIFY_BASE_SHA": base_sha})

    assert result.returncode == 1
    assert "conductor/ci/reports/generated.md" in result.stderr

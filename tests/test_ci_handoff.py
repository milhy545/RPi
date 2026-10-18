from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HANDOFF_SCRIPT = PROJECT_ROOT / "tools" / "trigger-ci-handoff.sh"


def _run_handoff_command(repo: Path, command: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        ["bash", "-c", command],
        cwd=repo,
        capture_output=True,
        text=True,
        env=merged_env,
        check=False,
    )


def _prepare_repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "conductor" / "ci" / "receipts").mkdir(parents=True, exist_ok=True)
    (root / "conductor" / "ci" / "reports").mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "--initial-branch=main", str(root)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "ci@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "CI Test"], check=True)
    (root / "README.md").write_text("handoff test\n")
    subprocess.run(["git", "-C", str(root), "add", "README.md"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-m", "test"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(root), "remote", "add", "origin", "https://github.com/example/repo.git"],
        check=True,
    )
    return root


def test_import_main_receipt_for_sha_creates_local_receipt_and_report(tmp_path: Path) -> None:
    repo = _prepare_repo(tmp_path / "repo")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()

    gh = fake_bin / "gh"
    gh.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
case "$*" in
  *'actions/runs?head_sha='*)
    cat <<'JSON'
{"workflow_runs":[{"head_sha":"__SHA__","head_branch":"main","event":"push","status":"completed","conclusion":"success","path":".github/workflows/ci.yml","html_url":"https://github.com/example/repo/actions/runs/123"}]}
JSON
    ;;
  *)
    echo "unexpected gh call: $*" >&2
    exit 1
    ;;
esac
""".replace("__SHA__", sha)
    )
    gh.chmod(0o755)

    result = _run_handoff_command(
        repo,
        f'source "{HANDOFF_SCRIPT}" && import_main_receipt_for_sha "{sha}"',
        env={
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
            "ROOT": str(repo),
            "IMPORT_MAIN_RECEIPT_SCRIPT": str(PROJECT_ROOT / "tools" / "import_main_receipt.py"),
        },
    )

    assert result.returncode == 0, result.stderr
    assert "Imported local CI receipt for exact main commit" in result.stdout
    receipt = next((repo / "conductor" / "ci" / "receipts").glob(f"{sha}-*.json"))
    report = next((repo / "conductor" / "ci" / "reports").glob(f"{sha[:7]}-*.md"))
    assert '"source": "github-actions-main-push"' in receipt.read_text()
    assert report.read_text().startswith("PASS: GitHub Actions push CI")


def test_import_main_receipt_for_sha_skips_when_already_present(tmp_path: Path) -> None:
    repo = _prepare_repo(tmp_path / "repo")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    report = repo / "conductor" / "ci" / "reports" / f"{sha[:7]}-cached.md"
    report.write_text("PASS\n")
    receipt = repo / "conductor" / "ci" / "receipts" / f"{sha}-cached.json"
    receipt.write_text(
        json.dumps(
            {
                "commit_sha": sha,
                "source": "github-actions-main-push",
                "ci_report": str(report.relative_to(repo)),
            }
        )
    )

    gh = fake_bin / "gh"
    gh.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
echo 'gh should not be called when receipt and report already exist' >&2
exit 1
"""
    )
    gh.chmod(0o755)

    result = _run_handoff_command(
        repo,
        f'source "{HANDOFF_SCRIPT}" && import_main_receipt_for_sha "{sha}"',
        env={"PATH": f"{fake_bin}:{os.environ['PATH']}", "ROOT": str(repo)},
    )

    assert result.returncode == 0, result.stderr
    assert "already present locally" in result.stdout


def test_handoff_selectively_includes_exact_rpi_candidate_receipt(tmp_path: Path) -> None:
    repo = _prepare_repo(tmp_path / "repo")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    args_file = tmp_path / "rsync-args.txt"
    fake_rsync = fake_bin / "rsync"
    fake_rsync.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' \"$@\" > \"$RSYNC_ARGS_FILE\"\n"
    )
    fake_rsync.chmod(0o755)
    sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    receipt = repo / "conductor" / "ci" / "receipts" / f"{sha}-receipt.json"
    receipt.write_text('{"commit_sha":"' + sha + '"}\n')
    other_receipt = repo / "conductor" / "ci" / "receipts" / "unrelated-receipt.json"
    other_receipt.write_text('{"commit_sha":"unrelated"}\n')

    result = _run_handoff_command(
        repo,
        f'source "{HANDOFF_SCRIPT}" && sync_repo_to_milhy_pc "{sha}"',
        env={
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
            "ROOT": str(repo),
            "STATE_FILE": str(tmp_path / "handoff-state"),
            "RSYNC_ARGS_FILE": str(args_file),
            "MILHY_PC_HOST": "test-host",
            "MILHY_PC_REPO": "/tmp/rpi-test",
        },
    )

    assert result.returncode == 0, result.stderr
    args = args_file.read_text().splitlines()
    candidate_filter = f"--include=/conductor/ci/receipts/{sha}-receipt.json"
    receipt_exclude_filter = "--exclude=/conductor/ci/receipts/***"
    assert candidate_filter in args
    assert args.index(candidate_filter) < args.index(receipt_exclude_filter)
    assert not any("unrelated-receipt.json" in arg for arg in args)
    assert any(
        args[index] == "--exclude" and args[index + 1] == "/conductor/ci/reports/"
        for index in range(len(args) - 1)
    )


def test_handoff_protects_local_receipts_and_reports_from_rsync_delete() -> None:
    script = HANDOFF_SCRIPT.read_text()

    assert "--exclude '/conductor/ci/reports/'" in script
    assert "--exclude='/conductor/ci/receipts/***'" in script


def test_rsync_handoff_filter_keeps_only_candidate_and_preserves_local_files(tmp_path: Path) -> None:
    rsync = shutil.which("rsync")
    assert rsync is not None, "rsync is required to validate the CI handoff filters"
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source_receipts = source / "conductor" / "ci" / "receipts"
    destination_receipts = destination / "conductor" / "ci" / "receipts"
    source_reports = source / "conductor" / "ci" / "reports"
    destination_reports = destination / "conductor" / "ci" / "reports"
    source_receipts.mkdir(parents=True)
    destination_receipts.mkdir(parents=True)
    source_reports.mkdir(parents=True)
    destination_reports.mkdir(parents=True)

    candidate = "a" * 40 + "-receipt.json"
    (source_receipts / candidate).write_text("candidate\n")
    (source_receipts / "unrelated-receipt.json").write_text("unrelated\n")
    (destination_receipts / "local-only-receipt.json").write_text("local\n")
    (source_reports / "generated.md").write_text("source report\n")
    (destination_reports / "local-only.md").write_text("local report\n")

    result = subprocess.run(
        [
            rsync,
            "-a",
            "--delete",
            "--dry-run",
            "--itemize-changes",
            "--include=/conductor/",
            "--include=/conductor/ci/",
            "--include=/conductor/ci/receipts/",
            f"--include=/conductor/ci/receipts/{candidate}",
            "--exclude=/conductor/ci/receipts/***",
            "--exclude=/conductor/ci/reports/",
            f"{source}/",
            f"{destination}/",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert candidate in result.stdout
    assert "unrelated-receipt.json" not in result.stdout
    assert "local-only-receipt.json" not in result.stdout
    assert "generated.md" not in result.stdout
    assert "local-only.md" not in result.stdout

from __future__ import annotations

import os
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
    sha = "b" * 40

    (repo / "conductor" / "ci" / "receipts" / f"{sha}-cached.json").write_text("{}")
    (repo / "conductor" / "ci" / "reports" / f"{sha}-cached.md").write_text("PASS\n")

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


def test_handoff_protects_local_receipts_and_reports_from_rsync_delete() -> None:
    script = HANDOFF_SCRIPT.read_text()

    assert "--exclude 'conductor/ci/reports/'" in script
    assert "--exclude 'conductor/ci/receipts/'" in script

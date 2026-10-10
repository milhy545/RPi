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
    (root / "conductor" / "ci" / "receipts").mkdir(parents=True, exist_ok=True)
    (root / "conductor" / "ci" / "reports").mkdir(parents=True, exist_ok=True)
    return root


def test_download_ci_artifacts_for_sha_copies_receipt_and_report(tmp_path: Path) -> None:
    repo = _prepare_repo(tmp_path / "repo")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    sha = "a" * 40

    gh = fake_bin / "gh"
    gh.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
case "$*" in
  *'run list'*)
    cat <<'JSON'
[{"databaseId": 123, "headSha": "__SHA__", "headBranch": "main", "event": "push", "status": "completed", "conclusion": "success"}]
JSON
    ;;
  *'run download'*)
    dest=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        -D)
          dest="$2"
          shift 2
          ;;
        *)
          shift
          ;;
      esac
    done
    mkdir -p "$dest/ci-receipt" "$dest/ci-report-ubuntu"
    cat > "$dest/ci-receipt/__SHA__-github-main.json" <<'JSON'
{"status":"done","commit_sha":"__SHA__","tree_hash":"tree","ci_report":"report.md","actions_url":"https://example.invalid"}
JSON
    cat > "$dest/ci-report-ubuntu/__SHA__-github-main.md" <<'MD'
PASS
MD
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
        f'source "{HANDOFF_SCRIPT}" && download_ci_artifacts_for_sha "{sha}"',
        env={"PATH": f"{fake_bin}:{os.environ['PATH']}", "ROOT": str(repo)},
    )

    assert result.returncode == 0, result.stderr
    assert "Downloaded CI artifacts for" in result.stdout
    receipt = next((repo / "conductor" / "ci" / "receipts").glob(f"{sha}-*.json"))
    report = next((repo / "conductor" / "ci" / "reports").glob(f"{sha}-*.md"))
    assert receipt.read_text().startswith('{"status":"done"')
    assert report.read_text().strip() == "PASS"


def test_download_ci_artifacts_for_sha_skips_when_already_synced(tmp_path: Path) -> None:
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
echo 'gh should not be called when artifacts already exist' >&2
exit 1
"""
    )
    gh.chmod(0o755)

    result = _run_handoff_command(
        repo,
        f'source "{HANDOFF_SCRIPT}" && download_ci_artifacts_for_sha "{sha}"',
        env={"PATH": f"{fake_bin}:{os.environ['PATH']}", "ROOT": str(repo)},
    )

    assert result.returncode == 0, result.stderr
    assert "already present locally" in result.stdout

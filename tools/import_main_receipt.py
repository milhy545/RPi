#!/usr/bin/env python3
"""Import an exact-main GitHub Actions push run as a local CI receipt."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any


def select_successful_main_run(runs: list[dict[str, Any]], commit_sha: str) -> dict[str, Any] | None:
    for run in runs:
        if (
            run.get("head_sha") == commit_sha
            and run.get("head_branch") == "main"
            and run.get("event") == "push"
            and run.get("status") == "completed"
            and run.get("conclusion") == "success"
            and run.get("path") == ".github/workflows/ci.yml"
        ):
            return run
    return None


def repository_from_origin(origin: str) -> str:
    match = re.search(r"github\.com[/:]([^/]+/[^/]+?)(?:\.git)?$", origin)
    if match is None:
        raise ValueError("origin is not a GitHub repository")
    return match.group(1)


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def main() -> int:
    if len(sys.argv) != 5:
        print(
            "usage: import_main_receipt.py RECEIPT_DIR REPORT_DIR COMMIT_SHA TREE_HASH",
            file=sys.stderr,
        )
        return 2
    receipt_dir, report_dir = Path(sys.argv[1]), Path(sys.argv[2])
    commit_sha, tree_hash = sys.argv[3], sys.argv[4]
    origin = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    repository = repository_from_origin(origin)
    api = subprocess.run(
        [
            "gh",
            "api",
            "--method",
            "GET",
            f"repos/{repository}/actions/runs?head_sha={commit_sha}&branch=main&event=push&status=success&per_page=100",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    run = select_successful_main_run(json.loads(api.stdout).get("workflow_runs", []), commit_sha)
    if run is None:
        print("No successful exact-main push CI run found", file=sys.stderr)
        return 1

    receipt_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    report = report_dir / f"{commit_sha[:7]}-{stamp}-github-main.md"
    report.write_text(
        f"PASS: GitHub Actions push CI for exact main commit\n"
        f"Commit: {commit_sha}\nRun: {run['html_url']}\n"
    )
    receipt = receipt_dir / f"{commit_sha}-{stamp}-github-main.json"
    atomic_json(
        receipt,
        {
            "status": "done",
            "commit_sha": commit_sha,
            "tree_hash": tree_hash,
            "source": "github-actions-main-push",
            "ci_report": str(report),
            "actions_url": run["html_url"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    print(receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

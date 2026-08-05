"""Isolated candidate staging and worktree management for RPi validation.

Ensures candidate code is built/tested in isolated worktrees outside live
checkout, refusing dirty worktree overrides and providing clean rollback.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import logging
from .rpi_guard import DirtyCheckoutError, SHAMismatchError

logger = logging.getLogger(__name__)


def is_git_dirty(repo_dir: str) -> bool:
    """Check if repository directory has uncommitted dirty changes."""
    if not os.path.exists(repo_dir):
        return False
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        return len(res.stdout.strip()) > 0
    except Exception as e:
        logger.warning(f"Could not check git status in {repo_dir}: {e}")
        return False


def get_head_sha(repo_dir: str) -> str:
    """Get current HEAD SHA of repository directory."""
    res = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=True,
    )
    return res.stdout.strip()


def stage_candidate(
    source_dir: str,
    target_dir: str,
    commit_sha: str,
    clean_target_first: bool = True,
) -> str:
    """Stage exact commit SHA into target_dir outside live checkout.

    Refuses staging if source_dir or target_dir has uncommitted dirty changes.
    """
    source_dir = os.path.abspath(source_dir)
    target_dir = os.path.abspath(target_dir)

    # Protection: Never overwrite live checkout directly as target
    if target_dir == source_dir:
        raise DirtyCheckoutError("Target directory cannot be identical to live source checkout.")

    # Rule: Refuse if live checkout is dirty
    if is_git_dirty(source_dir):
        raise DirtyCheckoutError(f"Live source checkout '{source_dir}' has uncommitted dirty changes. Refusing staging.")

    # Rule: Refuse if target directory exists and is dirty
    if os.path.exists(target_dir) and is_git_dirty(target_dir):
        raise DirtyCheckoutError(f"Target directory '{target_dir}' exists and contains uncommitted dirty changes. Refusing rsync/overwrite.")

    if clean_target_first and os.path.exists(target_dir):
        shutil.rmtree(target_dir)

    os.makedirs(target_dir, exist_ok=True)

    # Sync code excluding runtime artifacts
    excludes = [
        ".venv/",
        "__pycache__/",
        "*.pyc",
        ".forensics/",
        "conductor/ci/reports/",
        "conductor/ci/receipts/",
        "playback-memory.json",
        "yt-cookies.txt",
    ]
    rsync_cmd = ["rsync", "-a", "--delete"]
    for exc in excludes:
        rsync_cmd.extend(["--exclude", exc])
    rsync_cmd.extend([f"{source_dir}/", f"{target_dir}/"])

    subprocess.run(rsync_cmd, check=True)

    # Verify staged SHA matches expected commit_sha
    staged_sha = get_head_sha(target_dir)
    if staged_sha != commit_sha:
        # Cleanup failed candidate
        rollback_candidate(target_dir)
        raise SHAMismatchError(f"Staged SHA mismatch: expected '{commit_sha}', got '{staged_sha}'. Target rolled back.")

    logger.info(f"Successfully staged candidate {commit_sha} at {target_dir}")
    return target_dir


def rollback_candidate(target_dir: str) -> None:
    """Safely roll back and clean up staged candidate directory."""
    target_dir = os.path.abspath(target_dir)
    if os.path.exists(target_dir):
        try:
            shutil.rmtree(target_dir)
            logger.info(f"Rolled back candidate worktree: {target_dir}")
        except Exception as e:
            logger.error(f"Failed to remove candidate worktree {target_dir}: {e}")

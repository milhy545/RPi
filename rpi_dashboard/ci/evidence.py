"""Lock ownership, evidence struct, and atomic receipt validation.

Manages pipeline flock locks, builds evidence contracts, and validates
atomic receipts across host execution profiles.
"""

from __future__ import annotations

import fcntl
import time
import datetime
import logging
from typing import Dict, List, Any, Optional
from .rpi_guard import LockContentionError

logger = logging.getLogger(__name__)


class PipelineLock:
    """Context manager for acquiring pipeline flock lock."""

    def __init__(self, lock_path: str = "/tmp/rpi-ci-pipeline.lock", timeout_seconds: float = 5.0, lock_file_path: Optional[str] = None):
        self.lock_path = lock_file_path if lock_file_path is not None else lock_path
        self.timeout_seconds = timeout_seconds
        self._file_obj = None

    def __enter__(self):
        self._file_obj = open(self.lock_path, "w")
        start = time.time()
        while True:
            try:
                fcntl.flock(self._file_obj.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except (BlockingIOError, IOError):
                if time.time() - start >= self.timeout_seconds:
                    self._file_obj.close()
                    raise LockContentionError(
                        f"Could not acquire pipeline lock '{self.lock_path}' within {self.timeout_seconds}s. Pipeline is locked by another process."
                    )
                time.sleep(0.2)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._file_obj:
            try:
                fcntl.flock(self._file_obj.fileno(), fcntl.LOCK_UN)
                self._file_obj.close()
            except Exception:
                pass


def build_evidence_record(
    host: str,
    commit_sha: str,
    tree_hash: str,
    profile: str,
    reports: List[str],
    rpi_gate: Dict[str, Any],
    e2e_artifacts: List[str],
    actions_url: str,
    receipt_path: str,
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    """Build standardized evidence payload binding all pipeline outputs."""
    if timestamp is None:
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    return {
        "host": host,
        "commit_sha": commit_sha,
        "tree_hash": tree_hash,
        "profile": profile,
        "timestamp": timestamp,
        "reports": reports,
        "rpi_gate": rpi_gate,
        "e2e_artifacts": e2e_artifacts,
        "actions_url": actions_url,
        "receipt": receipt_path,
    }


def validate_receipt_structure(receipt_data: Dict[str, Any], expected_sha: Optional[str] = None, expected_tree: Optional[str] = None) -> bool:
    """Validate receipt structure, SHA binding, and completion status."""
    if receipt_data.get("status") != "done":
        return False
    if not receipt_data.get("commit_sha"):
        return False

    if expected_sha and receipt_data.get("commit_sha") != expected_sha:
        return False

    if expected_tree and receipt_data.get("tree_hash") != expected_tree:
        return False

    actions_url = receipt_data.get("actions_url", "")
    if not actions_url or not actions_url.startswith("https://"):
        return False

    ci_report = receipt_data.get("ci_report", "")
    if not ci_report:
        return False

    return True

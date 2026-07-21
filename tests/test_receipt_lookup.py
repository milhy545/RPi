import json
from pathlib import Path
import subprocess
import sys


LOOKUP = Path(__file__).parents[1] / "tools" / "receipt_lookup.py"


def _receipt(path: Path, *, commit_sha: str, tree_hash: str) -> Path:
    path.write_text(json.dumps({"commit_sha": commit_sha, "tree_hash": tree_hash}))
    return path


def _lookup(receipt_dir: Path, commit_sha: str, tree_hash: str) -> str:
    result = subprocess.run(
        [sys.executable, str(LOOKUP), str(receipt_dir), commit_sha, tree_hash],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def test_exact_commit_receipt_takes_priority_over_tree_match(tmp_path: Path) -> None:
    tree_receipt = _receipt(tmp_path / "z-tree.json", commit_sha="old", tree_hash="tree")
    exact_receipt = _receipt(tmp_path / "a-exact.json", commit_sha="head", tree_hash="other")

    assert _lookup(tmp_path, "head", "tree") == str(exact_receipt)
    assert tree_receipt != exact_receipt


def test_rebased_commit_can_reuse_identical_tree_receipt(tmp_path: Path) -> None:
    receipt = _receipt(tmp_path / "receipt.json", commit_sha="before-rebase", tree_hash="tree")

    assert _lookup(tmp_path, "after-rebase", "tree") == str(receipt)


def test_receipt_with_different_tree_is_rejected(tmp_path: Path) -> None:
    _receipt(tmp_path / "receipt.json", commit_sha="other", tree_hash="different")

    assert _lookup(tmp_path, "head", "tree") == ""


def test_malformed_receipt_is_ignored(tmp_path: Path) -> None:
    (tmp_path / "z-malformed.json").write_text("not json")
    receipt = _receipt(tmp_path / "a-valid.json", commit_sha="head", tree_hash="tree")

    assert _lookup(tmp_path, "head", "tree") == str(receipt)

#!/usr/bin/env python3
"""Find the newest CI receipt matching a commit SHA or Git tree hash."""

from __future__ import annotations

import json
from pathlib import Path
import sys


def find_receipt(receipt_dir: Path, commit_sha: str, tree_hash: str) -> Path | None:
    receipts = sorted(receipt_dir.glob("*.json"), reverse=True)
    tree_match = None
    for receipt in receipts:
        try:
            payload = json.loads(receipt.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("commit_sha") == commit_sha:
            return receipt
        if tree_match is None and payload.get("tree_hash") == tree_hash:
            tree_match = receipt
    return tree_match


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: receipt_lookup.py RECEIPT_DIR COMMIT_SHA TREE_HASH", file=sys.stderr)
        return 2
    receipt = find_receipt(Path(sys.argv[1]), sys.argv[2], sys.argv[3])
    if receipt is not None:
        print(receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

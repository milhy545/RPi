#!/usr/bin/env python3
"""Find the newest CI receipt matching a commit SHA or Git tree hash."""

from __future__ import annotations

import json
from pathlib import Path
import sys


def find_receipt(
    receipt_dir: Path,
    commit_sha: str,
    tree_hash: str,
    *,
    source: str | None = None,
    exact_sha: bool = False,
) -> Path | None:
    receipts = sorted(receipt_dir.glob("*.json"), reverse=True)
    tree_match = None
    for receipt in receipts:
        try:
            payload = json.loads(receipt.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if source is not None and payload.get("source") != source:
            continue
        if payload.get("commit_sha") == commit_sha:
            return receipt
        if not exact_sha and tree_match is None and payload.get("tree_hash") == tree_hash:
            tree_match = receipt
    return tree_match


def main() -> int:
    arguments = sys.argv[1:]
    source = None
    exact_sha = False
    positional: list[str] = []
    while arguments:
        argument = arguments.pop(0)
        if argument == "--source" and arguments:
            source = arguments.pop(0)
        elif argument == "--exact-sha":
            exact_sha = True
        else:
            positional.append(argument)
    if len(positional) != 3:
        print(
            "usage: receipt_lookup.py RECEIPT_DIR COMMIT_SHA TREE_HASH [--source SOURCE] [--exact-sha]",
            file=sys.stderr,
        )
        return 2
    receipt = find_receipt(
        Path(positional[0]),
        positional[1],
        positional[2],
        source=source,
        exact_sha=exact_sha,
    )
    if receipt is not None:
        print(receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

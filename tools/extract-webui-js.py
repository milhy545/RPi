#!/usr/bin/env python3
"""Extract embedded WebUI JavaScript from webserver.py for syntax checks."""
from __future__ import annotations

from pathlib import Path
import sys


def main() -> int:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("webserver.py")
    text = source.read_text(encoding="utf-8")
    marker = 'JS=r"""'
    start = text.find(marker)
    if start < 0:
        print(f"ERROR: {source}: JS block marker not found", file=sys.stderr)
        return 2
    start += len(marker)
    end = text.find('"""', start)
    if end < 0:
        print(f"ERROR: {source}: JS block terminator not found", file=sys.stderr)
        return 2
    sys.stdout.write(text[start:end])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

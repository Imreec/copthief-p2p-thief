"""Enforce CLAUDE.md §1 rule 1: every Python file ≤ 150 source lines (tests included).

Source lines = non-blank lines that are not pure comments. Split files, never compress.
"""

from __future__ import annotations

import sys
from pathlib import Path

LIMIT = 150
SCAN_DIRS = ("src", "tests", "scripts")


def source_lines(path: Path) -> int:
    """Count non-blank, non-comment-only lines in a Python file."""
    count = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            count += 1
    return count


def main() -> int:
    """Scan SCAN_DIRS; report every file over LIMIT; exit 1 if any."""
    offenders: list[tuple[str, int]] = []
    for base in SCAN_DIRS:
        root = Path(base)
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            n = source_lines(path)
            if n > LIMIT:
                offenders.append((str(path), n))
    if offenders:
        print(f"FAIL: files over {LIMIT} source lines (split, never compress):")
        for name, n in offenders:
            print(f"  {n:4d}  {name}")
        return 1
    print(f"OK: all Python files within {LIMIT} source lines.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Enforce config ownership (CLAUDE.md §1 rule 5): no config-owned literals in src/.

Every quantitative game value and every destination lives in config/game.json /
config/game.toml / config/rate_limits.json. This scanner catches the classic leaks;
the code-review gate catches the rest.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Literals that must never appear in source code (they are config-owned).
FORBIDDEN = [
    (r"rmisegal", "lecturer address is config-owned (game.toml [email])"),
    (r"uoh26", "report mailbox is config-owned (game.toml [email])"),
    (r"@gmail\.com", "email addresses are config-owned"),
    (r"https?://[\w.-]*(ngrok|trycloudflare|localtonet)", "tunnel URLs are config-owned"),
    (r"localhost:\d{4,5}", "host:port endpoints are config-owned"),
    (r"127\.0\.0\.1:\d{4,5}", "host:port endpoints are config-owned"),
]


def main() -> int:
    """Scan src/ for forbidden config-owned literals; exit 1 on any hit."""
    root = Path("src")
    problems: list[str] = []
    if root.is_dir():
        for path in sorted(root.rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            for pattern, why in FORBIDDEN:
                for m in re.finditer(pattern, text, flags=re.IGNORECASE):
                    line = text[: m.start()].count("\n") + 1
                    problems.append(f"{path}:{line}: {m.group(0)!r} — {why}")
    if problems:
        print("FAIL: hardcoded config-owned values in src/:")
        for p in problems:
            print(f"  {p}")
        return 1
    print("OK: no hardcoded config-owned literals in src/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

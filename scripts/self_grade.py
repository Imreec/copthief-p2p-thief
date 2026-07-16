"""Self-grade calculator — CODE QUALITY ONLY, never league results (book App E rule 55).

Reads config/self_grade.json (categories: name, weight, score, justification), prints the
weighted breakdown. ``--validate`` checks structure only (CI mode): weights sum to 100,
scores in [0, 100], every category justified. Honesty rules live in .claude/skills/self-grade.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

CONFIG = Path("config/self_grade.json")
CAP = 95


def load() -> list[dict[str, object]]:
    """Load and structurally validate the categories list."""
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    cats: list[dict[str, object]] = data["categories"]
    weights = sum(int(c["weight"]) for c in cats)
    if weights != 100:
        raise ValueError(f"weights sum to {weights}, must be 100")
    for c in cats:
        score = float(c["score"])  # type: ignore[arg-type]
        if not 0 <= score <= 100:
            raise ValueError(f"{c['name']}: score {score} outside [0, 100]")
        if not str(c["justification"]).strip():
            raise ValueError(f"{c['name']}: justification required")
    return cats


def main() -> int:
    """Validate; unless --validate, print the weighted breakdown and total."""
    try:
        cats = load()
    except (OSError, KeyError, ValueError) as exc:
        print(f"FAIL: self_grade config invalid: {exc}")
        return 1
    if "--validate" in sys.argv:
        print("OK: self_grade.json structurally valid.")
        return 0
    total = sum(float(c["score"]) * int(c["weight"]) / 100 for c in cats)  # type: ignore[arg-type]
    print(f"{'Category':44} {'W':>3} {'Score':>6}")
    for c in cats:
        print(f"{str(c['name']):44} {int(c['weight']):3d} {float(c['score']):6.1f}")  # type: ignore[arg-type]
    print(f"{'TOTAL':44} {'100':>3} {total:6.1f}")
    if total > CAP:
        print(f"WARNING: total exceeds the {CAP} reporting cap — re-audit before claiming.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

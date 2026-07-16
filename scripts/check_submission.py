"""Living submission checklist (book App C table 6 + guidelines section 17) — TODO M0-8.

Non-blocking report by default (M0-M7): prints PASS/PENDING per item, always exits 0.
``--strict`` (M8): every item must PASS or the script exits 1. Checks are mechanical
where possible; items needing human/GitHub state are marked MANUAL. Output stays
ASCII-only: Windows consoles default to cp1252 and crash on unicode glyphs.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

README_SECTIONS = [  # book §9.4.2 mandatory headings (asserted once README report exists)
    "Dec-POMDP",
    "Orchestration dilemmas",
    "Strategies",
    "Screenshots",
]


def _exists(path: str) -> bool:
    return Path(path).exists()


def _tag_exists(tag: str) -> bool:
    out = subprocess.run(["git", "tag", "-l", tag], capture_output=True, text=True, check=False)
    return tag in out.stdout


def checks() -> list[tuple[str, bool | None]]:
    """(item, state) — True=PASS, False=PENDING, None=MANUAL."""
    readme = Path("README.md").read_text(encoding="utf-8") if _exists("README.md") else ""
    return [
        (
            "docs/PRD.md + PLAN.md + TODO.md present",
            all(_exists(f"docs/{n}.md") for n in ("PRD", "PLAN", "TODO")),
        ),
        ("CLAUDE.md present", _exists("CLAUDE.md")),
        (
            "docs/REVIEW_PROCESS.md + PROMPTS.md present",
            all(_exists(f"docs/{n}.md") for n in ("REVIEW_PROCESS", "PROMPTS")),
        ),
        ("ADRs present (docs/adr/)", _exists("docs/adr")),
        ("config/ committed", _exists("config")),
        ("README report sections", all(s.lower() in readme.lower() for s in README_SECTIONS)),
        (
            "Belief-heatmap screenshot (assets/)",
            any(Path("assets").glob("*belief*")) if _exists("assets") else False,
        ),
        (
            "Replay Verified-OK screenshot (assets/)",
            any(Path("assets").glob("*verified*")) if _exists("assets") else False,
        ),
        ("Sibling repo cross-link in README", "copthief-p2p-" in readme),
        (
            "KNOWN_LIMITATIONS.md / SELF_GRADE.md / COST.md",
            all(_exists(n) for n in ("KNOWN_LIMITATIONS.md", "SELF_GRADE.md", "COST.md")),
        ),
        ("Annotated tag v1.0-submission", _tag_exists("v1.0-submission")),
        (
            "No secrets tracked (spot check)",
            not any(
                _exists(n) and _tracked(n) for n in ("client_secret.json", "token.json", ".env")
            ),
        ),
        (">=2 counted series vs distinct teams", None),
        ("Both end-of-game emails sent (each team separately)", None),
        ("Repos shared with the lecturer", None),
        ("Moodle per-member submission + PDF form + group ID", None),
    ]


def _tracked(path: str) -> bool:
    out = subprocess.run(
        ["git", "ls-files", "--error-unmatch", path], capture_output=True, check=False
    )
    return out.returncode == 0


def main() -> int:
    """Print the checklist; --strict fails on any non-PASS mechanical item."""
    strict = "--strict" in sys.argv
    failed = False
    for item, state in checks():
        label = "MANUAL" if state is None else ("PASS" if state else "PENDING")
        if state is not True:
            failed = True
        print(f"  [{label:7}] {item}")
    if strict and failed:
        print("STRICT: submission checklist incomplete.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

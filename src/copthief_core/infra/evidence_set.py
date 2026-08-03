"""The four-template evidence set beside a result artifact (M7-37, split from
email_sender per the 150-line rule).

Moodle item 4 (the grader's own instruction, screenshot-verified 2026-08-03): the
agent sends the lecturer the four attached JSON templates at game end. Superset
resolution agreed with the opponent team: the ONE series email attaches every
instance of all four types; the result stays the body and the named attachment.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["evidence_set"]


def evidence_set(result_path: Path, game_id: str) -> list[tuple[str, bytes]]:
    """The rest of the four-template set beside `result_path`, in Table-20 order.

    Declaration first, then per-game configs and logs sorted by window. Globs the
    three template prefixes only, so the Hebrew per-game `report_*` files never
    ride. Missing siblings are simply absent — presence is REPORTED in the send
    outcome, never load-bearing (rule 35 punishes the missing report, not a thin
    mail).
    """
    if not game_id:
        return []
    home = result_path.parent
    names = [
        path.name
        for pattern in (
            f"declaration_{game_id}.json",
            f"config_{game_id}_g*.json",
            f"log_{game_id}_g*.json",
        )
        for path in sorted(home.glob(pattern))
    ]
    return [(name, (home / name).read_bytes()) for name in names]

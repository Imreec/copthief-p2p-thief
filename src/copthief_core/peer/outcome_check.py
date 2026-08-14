"""Audit-time outcome re-derivation (M11 part 2 follow-up) — derived, never declared,
applied END-TO-END.

Live finding (best2934 friendly, 2026-08-14 g02/g04): our cop imprisoned their
thief at (6,6) by step 13 (rule 47 — imprisonment IS capture), their engine never
emitted the boxed-in concession, and both sub-games settled as 35-step
"survivals" while the disclosed trail in our own audit refuted the score. Live
play cannot catch this (positions are hidden; the concession is the loser's
duty), but at audit the blindness is gone: their revealed walk + the final board
make the contradiction pure geometry.

The check is a LOUD EVENT, never a verdict change (the M6-7/SQ3 posture, and
deliberately so): a problems[] entry accuses the peer of forgery, and the
wall-timing boundary (a seal completing on the final turn leaves no concession
window) makes a hard verdict unsafe against an honest opponent. Requiring the
imprisoned cell to be HELD across at least two revealed steps removes that
boundary; a vacuous run says so instead of reading as a clean pass (M7-58).
Escalating the event into a counted-report gate is a documented follow-up,
pending league validation of its precision.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from copthief_core.domain.board import Board
from copthief_core.domain.rules import is_imprisoned
from copthief_core.peer.scent_records import revealed_positions

__all__ = ["emit_outcome_check"]

LogFn = Callable[[dict[str, Any]], None]


def emit_outcome_check(theirs: dict[str, Any], board: Board, emit: LogFn) -> None:
    """Diff a thief 'survival' claim against its own revealed trail (Input: the
    opponent's raw audit, the FINAL live board, the log sink; Output: none —
    evidence lands as `outcome_mismatch` / `outcome_check_vacuous` events)."""
    if theirs.get("result_claim") != "survival" or theirs.get("sender") != "thief":
        return
    records = theirs.get("records")
    if not isinstance(records, list):
        return
    positions = revealed_positions(records)
    if not positions:
        emit(
            {
                "event": "outcome_check_vacuous",
                "payload": {"reason": "no revealed coordinates in the opponent audit"},
            }
        )
        return
    steps = sorted(positions)
    final = positions[steps[-1]]
    held = 0
    for step in reversed(steps):
        if positions[step] != final:
            break
        held += 1
    if final in board.barriers:
        rule = 46  # a wall ON the thief's cell is capture, whenever it landed
    elif is_imprisoned(board, final) and held >= 2:
        # Held across >= 2 revealed steps: a full turn existed in which the
        # boxed-in concession was due, so final-turn seal timing cannot excuse it.
        rule = 47
    else:
        return
    emit(
        {
            "event": "outcome_mismatch",
            "payload": {
                "claim": "survival",
                "rule": rule,
                "cell": list(final),
                "held_steps": held,
                "detail": (
                    "revealed trail contradicts the settled outcome: the final revealed "
                    "cell is captured under the final board (derived, never declared)"
                ),
            },
        }
    )

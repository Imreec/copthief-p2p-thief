"""Kinematic reach envelope (M11-2) — every cell the opponent could occupy.

Grown once per opponent turn from PHYSICS alone (legal moves + declared
barriers), deliberately independent of the probabilistic support, which
adversarial evidence (a lying hint's hard exclusion) can corrupt. Two consumers
in `BeliefFilter`: the claim plausibility gate — the M11 red-team verified that
the rules-21/22 sanction `note_claim` cited is enforced by no audit path, so an
IMPOSSIBLE claim is free adversarial input and must not collapse the belief —
and the degenerate-collapse reset, which recovers to a uniform over exactly
this set. For every truthful claimer the gate is a no-op by construction: a
true position is always inside its own motion envelope.
"""

from __future__ import annotations

from copthief_core.domain.board import Board, Coord
from copthief_core.domain.rules import legal_moves

__all__ = ["MotionEnvelope"]


class MotionEnvelope:
    """Cells reachable from the signed start in the elapsed opponent turns."""

    def __init__(self, start: Coord) -> None:
        self._cells: set[Coord] = {start}

    def spread(self, board: Board, move_set: tuple[str, ...]) -> None:
        """One opponent turn: grow by every legal action (STAY always possible —
        a live opponent on an open cell can hold it through any barrier turn)."""
        grown: set[Coord] = set()
        for cell in self._cells:
            if board.is_blocked(cell):
                continue
            grown.add(cell)
            for move in legal_moves(board, cell, move_set):
                grown.add(board.apply_move(cell, move))
        if grown:
            self._cells = grown

    def plausible(self, cell: Coord, board: Board) -> bool:
        """Could a live opponent be at `cell` right now?"""
        return cell in self._cells and not board.is_blocked(cell)

    def live_cells(self, board: Board) -> list[Coord]:
        """The open envelope, sorted — the degenerate-collapse reset prior."""
        return [c for c in sorted(self._cells) if not board.is_blocked(c)]

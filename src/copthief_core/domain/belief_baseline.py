"""Last-known-position baseline (PRD_belief §3): the naive tracker the filter must beat.

Point mass at the last cell any evidence CERTAINLY placed the opponent, else uniform.
"Certainly" means protocol-grade evidence only — the signed start or a proven claim
outcome. Scent grids are unauthenticated (SQ3) and freely fakeable, so this tracker
never reads them; that is exactly the naivety the Bayes filter is measured against.
"""

from __future__ import annotations

from copthief_core.domain.board import Board, Coord


class LastKnownTracker:
    """Interface-parity twin of BeliefFilter for the M3 evaluation loop."""

    def __init__(self, *, board: Board, start: Coord | None) -> None:
        self._board = board
        self._known = start

    def predict(self) -> None:
        """Turns passing never move a last-known point (that is the whole naivety)."""

    def update_scent(self, grid: dict[str, float]) -> None:
        """Unauthenticated evidence is never 'certain' — deliberately ignored."""

    def note_barrier(self, cell: Coord) -> None:
        """Barriers do not move a point estimate; kept for eval-loop parity."""

    def update_certain(self, cell: Coord) -> None:
        """Protocol-grade evidence (signed start, proven claim) moves the point mass."""
        self._known = cell

    def prob_at(self, cell: Coord) -> float:
        """Point mass on the known cell; uniform over the board when nothing is known."""
        if self._known is not None:
            return 1.0 if cell == self._known else 0.0
        return 1.0 / (self._board.grid_size * self._board.grid_size)

    def argmax(self) -> Coord:
        """The known cell, or the axis-origin cell when nothing is known (stable tie)."""
        if self._known is not None:
            return self._known
        origin = self._board.axis_start_index
        return (origin, origin)

    def belief_error(self, truth: Coord) -> float:
        """Primary M3 metric, same formula as the filter: 1 - P(truth)."""
        return 1.0 - self.prob_at(truth)

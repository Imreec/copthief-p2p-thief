"""Exact Bayes belief filter (book ch.6; PRD_belief §2): P(opponent at cell), exact.

The board is 49–100 cells, so exactness is affordable: plain float mass over a dict,
no sampling. Predict = uniform over the opponent's legal actions from each support
cell, constrained by every declared barrier (spike F9). Updates multiply likelihoods
and renormalize — and NEVER eliminate (SQ3: the scent grid is unauthenticated, so
fabricated evidence must degrade the estimate, never zero the truth or crash us).
Pure — no I/O, no clock, no RNG; all quantitative values arrive as arguments.
"""

from __future__ import annotations

import math
from collections.abc import Iterable

from copthief_core.domain.belief_baseline import LastKnownTracker
from copthief_core.domain.board import Board, Coord
from copthief_core.domain.rules import legal_moves

__all__ = ["BeliefFilter", "LastKnownTracker"]


class BeliefFilter:
    """One opponent's position distribution (Input: geometry + signed pheromone params
    + private trust weights + the opponent's signed start; Output: probability queries).
    """

    def __init__(
        self,
        *,
        board: Board,
        move_set: tuple[str, ...],
        start: Coord,
        center_intensity: float,
        decay: float,
        smell_trust: float,
        hint_trust: float,
    ) -> None:
        self._board = board
        self._move_set = move_set
        # The locked model's transmitted fresh-center value (PRD_scent §2).
        self._fresh = round(center_intensity - decay, 3)
        self._decay = decay
        self._smell_trust = smell_trust
        self._hint_trust = hint_trust
        self._probs: dict[Coord, float] = {start: 1.0}  # §2.1: the signed-start delta
        self._reachable: set[Coord] = {start}

    def note_barrier(self, cell: Coord) -> None:
        """A declared barrier (sealed, audited — certain) blocks motion AND occupancy."""
        self._board = self._board.with_barrier(cell)
        self._probs.pop(cell, None)
        self._normalize()

    def predict(self) -> None:
        """One opponent turn: mass splits uniformly over each support cell's legal
        actions (barriers excluded); stranded mass is rescaled by normalization."""
        spread: dict[Coord, float] = {}
        for cell, mass in self._probs.items():
            moves = list(legal_moves(self._board, cell, self._move_set))
            if "STAY" not in self._move_set and not self._board.is_blocked(cell):
                moves.append("STAY")  # §2.2: staying is always modeled (barrier turns)
            if not moves:
                continue
            share = mass / len(moves)
            for move in moves:
                dest = self._board.apply_move(cell, move)
                spread[dest] = spread.get(dest, 0.0) + share
        self._probs = spread
        self._reachable |= set(spread)
        self._normalize()

    def update_scent(self, grid: dict[str, float]) -> None:
        """§2.3: each received cell implies an age under the subtractive model (every
        missing `decay` of intensity ≈ one turn older), so it vouches for the opponent
        being within that many moves of it. The voucher's weight spreads over its
        Manhattan age-ball (`value / ball_size`) — a fresh center is a sharp spike,
        aged scent a wide whisper. Multiplies `1 + smell_trust * strongest_voucher`;
        never eliminates (floor 1)."""
        if self._smell_trust <= 0.0 or not grid:
            return
        vouchers = []
        for key, value in grid.items():
            if value <= 0.0:
                continue
            row, col = (int(part) for part in key.split(","))
            age = max(0, round((self._fresh - value) / self._decay)) if self._decay else 0
            ball_size = 2 * age * age + 2 * age + 1  # Manhattan ball, boundary-blind
            vouchers.append(((row, col), value / ball_size, age))
        if not vouchers:
            return
        for cell in self._probs:
            score = max(
                (
                    weight
                    for (src, weight, age) in vouchers
                    if abs(cell[0] - src[0]) + abs(cell[1] - src[1]) <= age
                ),
                default=0.0,
            )
            self._probs[cell] *= 1.0 + self._smell_trust * score
        self._normalize()

    def update_hint(self, cells: Iterable[Coord], weight: float | None = None) -> None:
        """§2.4 gazetteer seam: multiply the implied cells by `1 + weight` (clamped at
        0 — a -1 hard exclusion is allowed; total collapse is caught by the guard)."""
        factor = max(0.0, 1.0 + (self._hint_trust if weight is None else weight))
        implied = set(cells)
        for cell in self._probs:
            if cell in implied:
                self._probs[cell] *= factor
        self._normalize()

    def _normalize(self) -> None:
        """§2.5: renormalize; on degenerate collapse (contradictory fabricated
        evidence) reset to uniform over the motion-reachable set — never NaN/freeze."""
        self._probs = {c: p for c, p in self._probs.items() if p > 0.0}
        total = sum(self._probs.values())
        if not math.isfinite(total) or total <= 0.0:
            live = [c for c in sorted(self._reachable) if not self._board.is_blocked(c)]
            if not live:  # every reachable cell barriered: fall back to the open board
                origin = self._board.axis_start_index
                span = range(origin, origin + self._board.grid_size)
                live = [(r, c) for r in span for c in span if not self._board.is_blocked((r, c))]
            self._probs = {c: 1.0 / len(live) for c in live}
            return
        self._probs = {c: p / total for c, p in self._probs.items()}

    # -- read surface (GUI/brains consume ONLY these — PRD_belief §7) ----------------

    def probs(self) -> dict[Coord, float]:
        """The strictly-positive support (a copy)."""
        return dict(self._probs)

    def prob_at(self, cell: Coord) -> float:
        """P(opponent at cell), 0.0 outside the support."""
        return self._probs.get(cell, 0.0)

    def argmax(self) -> Coord:
        """Most probable cell; ties break to the smallest coordinate (deterministic)."""
        return min(self._probs.items(), key=lambda kv: (-kv[1], kv[0]))[0]

    def belief_error(self, truth: Coord) -> float:
        """The primary M3 metric (PRD_belief §3): 1 - P(truth)."""
        return 1.0 - self.prob_at(truth)

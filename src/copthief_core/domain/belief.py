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
from copthief_core.domain.belief_observation import (
    age_voucher_scores,
    innovation,
    kernel_match_scores,
    parse_grid,
)
from copthief_core.domain.board import Board, Coord
from copthief_core.domain.rules import legal_moves
from copthief_core.domain.scent_models import ScentModel, SubtractiveChebyshevV1

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
        scent_model: ScentModel | None = None,
    ) -> None:
        self._board = board
        self._move_set = move_set
        # M3-8: the OBSERVATION MODEL is the selected scent model (PRD_scent §9.3) — the
        # filter reads the falloff shape rather than assuming the reference's linear one.
        # Omitted, it is the reference form built from the signed terms, so every M3-3
        # measurement stands unchanged.
        self._scent = scent_model or SubtractiveChebyshevV1(
            {
                "field_size": 1,
                "emit_intensity": center_intensity,
                "min_center_intensity": 0.0,
                "decay_per_step": decay,
                "rounding_decimals": 3,
            }
        )
        self._smell_trust = smell_trust
        self._hint_trust = hint_trust
        self._probs: dict[Coord, float] = {start: 1.0}  # §2.1: the signed-start delta
        self._reachable: set[Coord] = {start}
        # M7-14: the previous observed field, for the kernel path's innovation.
        self._last_scent: dict[Coord, float] | None = None

    def note_barrier(self, cell: Coord) -> None:
        """A declared barrier (sealed, audited — certain) blocks motion AND occupancy."""
        self._board = self._board.with_barrier(cell)
        self._probs.pop(cell, None)
        self._normalize()

    def note_claim(self, cell: Coord) -> None:
        """A declared capture claim (sealed, sanctioned — certain): collapse onto `cell`.

        M7-18 / PRD_claims §4.1. The claim is a plaintext pre-reveal of a position already
        sealed in the same message's commit, and a false one costs the game with no appeal
        (App E rules 21-22) — so it is barrier-class evidence, not scent-class. The
        never-eliminate invariant (SQ3) guards against UNAUTHENTICATED grids and does not
        reach here. A claim outside the current support still collapses: the claim is
        truth, and our prior was simply wrong.
        """
        self._probs = {cell: 1.0}
        self._reachable.add(cell)

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
        """§2.3, dispatched on what a value MEANS under the selected model (M7-14):
        age vouchers when intensity encodes age (reference form — the M3-3 path,
        byte-identical), kernel shape-match when it does not (book form — saturation
        makes 'freshest cell' meaningless, but the fresh kernel's ring structure
        identifies its centre). Multiplies `1 + smell_trust * score`; never
        eliminates (floor 1)."""
        if self._smell_trust <= 0.0 or not grid:
            return
        support = list(self._probs)
        kernel = self._scent.spatial_kernel()
        if kernel is not None:
            # Shape-match the INNOVATION: what the decay-predicted past cannot
            # explain is (up to clamping) one fresh kernel at the current cell.
            observed = parse_grid(grid)
            residual = innovation(observed, self._last_scent, self._scent.decayed)
            self._last_scent = observed
            scores = kernel_match_scores(residual, support, kernel, self._board)
        else:
            scores = age_voucher_scores(grid, support, self._scent.age_of)
        if not scores:
            return
        for cell in support:
            self._probs[cell] *= 1.0 + self._smell_trust * scores.get(cell, 0.0)
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

"""best2934's pursuer as an arena arm (M7-45).

Modelled from their PUBLISHED brain at github.com/Krayz1a/best2934-cop
(`src/p2pchase/domain/cop_brain.py`, MIT License, (c) 2026 best2934 — Tomer Levy, Eyal
Koloshi, Alon Issman), linked from kit issue #45/#48. Companion to
`best2934_thief`; see it for the modelling stance.

`COP_DEFAULTS` carries the values they FIELD (`config/police/setup.json`), which for
the barrier gate is NOT their class default: first tuned 4 -> 1 on their own sweep,
then RE-derived 1 -> 4 on 2026-08-14 (max-min over 40 seeds x 5 thieves) — the change
that armed the evening plow that beat us 35-75. This is the parameter that decides
whether they are dangerous, so it is the one the tests pin hardest.

Rebuilt for M12 from offline study of their public code at 96d9b17 + our own
g01/g03/g05 logs. Two fidelity fixes: their `reachable_area(cell, limit=40)` is a
node budget that never binds on the negotiated 49-cell board (the old arm's clamp
read 40 on both sides of every open-board diff and silenced the waller — gain must
be the TRUE area shrink); and sealing onto the believed thief cell is their one veto
exemption (rule-46 capture, scored on the wire by their `boxed_in` fix since 08-14).
Their barrier search evaluates one cell at a time against the live board, which is
mirrored exactly — including the consequence that a two-wall seal, neither half of
which clears the gain bar alone, is invisible to it.
"""

from __future__ import annotations

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import STAY, Board, Coord
from copthief_core.domain.rules import legal_moves
from copthief_core.strategy.belief_distance import expected_distance
from copthief_core.strategy.brains import BrainBase, Observation
from copthief_core.strategy.decision import Decision
from copthief_core.strategy.region import path_length, region_size

__all__ = ["COP_DEFAULTS", "Best2934CopBrain"]

COP_DEFAULTS: dict[str, float] = {
    "barrier_engage_range": 4.0,  # FIELDED 08-14 re-derivation (was 1 before the plow)
    "barrier_min_gain": 1.0,  # cells a wall must remove from the thief's world
    "barrier_endgame_reserve": 3.0,  # walls held back for a finishable squeeze
    "endgame_squeeze_range": 2.0,  # inside the reserve, only wall this close
    "idle_penalty": 0.35,  # standing still is rarely right for a pursuer
    "mobility_weight": 0.01,  # keep our own escape routes open on ties
    "gap_penalty": 0.5,  # their `- 0.5 * (after_gap - before_gap)`
    "region_cap": 49.0,  # their limit=40 is a node budget; on 7x7 the area is TRUE
}


def _seal_candidates(board: Board, cop: Coord, move_set: tuple[str, ...]) -> set[Coord]:
    """The open cells within one step of the cop (their `barrier_targets`)."""
    destinations = {board.apply_move(cop, move) for move in move_set}
    return {cell for cell in destinations if cell != cop and not board.is_blocked(cell)}


class Best2934CopBrain(BrainBase):
    """Belief-driven pursuit with contact-range sealing (their `CopBrain`).

    Input:  the observation and our belief over the thief's cell.
    Output: a `Decision` — a barrier when one is worth the forgone step, else a move.
    Setup:  `COP_DEFAULTS`, overridable through the arena's `brain_options`.
    """

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        opts = {**COP_DEFAULTS, **self._options}
        board = observation.board
        candidates = sorted(legal_moves(board, observation.position, observation.move_set))
        if not candidates:
            return STAY
        cache: dict[Coord, int] = {}

        def score(move: str) -> float:
            """Lower is better: their `distance + idle - mobility_weight * area`."""
            dest = board.apply_move(observation.position, move)
            area = region_size(board, dest, observation.move_set, int(opts["region_cap"]), cache)
            penalty = opts["idle_penalty"] if move == STAY else 0.0
            return expected_distance(dest, belief) + penalty - opts["mobility_weight"] * area

        return min(candidates, key=lambda m: (score(m), m))

    def _decide(self, observation: Observation, belief: BeliefFilter) -> Decision:
        opts = {**COP_DEFAULTS, **self._options}
        target = belief.argmax()
        distance = abs(observation.position[0] - target[0]) + abs(
            observation.position[1] - target[1]
        )
        barrier = self._choose_barrier(observation, target, distance, opts)
        if barrier is not None:
            return Decision(move=STAY, barrier=barrier)
        return Decision(move=self._pick_move(observation, belief))

    @staticmethod
    def _engages(observation: Observation, distance: int, opts: dict[str, float]) -> bool:
        """Their cheap gates, checked before any flood fill (Output: consider a wall?)."""
        left = observation.max_barriers - observation.barriers_used
        if left <= 0 or distance > opts["barrier_engage_range"]:
            return False
        if left <= opts["barrier_endgame_reserve"]:
            return distance <= opts["endgame_squeeze_range"]
        return True

    def _choose_barrier(
        self,
        observation: Observation,
        target: Coord,
        distance: int,
        opts: dict[str, float],
    ) -> Coord | None:
        """Their one-cell-at-a-time wall search (Output: the cell to seal, or None)."""
        if not self._engages(observation, distance, opts):
            return None
        board = observation.board
        move_set, cap = observation.move_set, int(opts["region_cap"])
        before_area = region_size(board, target, move_set, cap, {})
        before_gap = path_length(board, observation.position, target, move_set)
        if before_gap is None:
            return None
        best: tuple[float, Coord] | None = None
        for cell in sorted(_seal_candidates(board, observation.position, move_set)):
            if cell == target:
                # Their one veto exemption: the wall ON the believed thief cell is
                # the rule-46 capture — severing our own route to it is the win.
                if best is None or before_area > best[0]:
                    best = (float(before_area), cell)
                continue
            walled = board.with_barrier(cell)
            gain = before_area - region_size(walled, target, move_set, cap, {})
            after_gap = path_length(walled, observation.position, target, move_set)
            # A wall that lengthens our own route to the thief — or severs it — is
            # refused however much area it removes. Theirs runs the same test, and it
            # is what stops greedy walling from sealing the cop out of its own hunt.
            if after_gap is None or after_gap > before_gap or gain < opts["barrier_min_gain"]:
                continue
            value = gain - opts["gap_penalty"] * (after_gap - before_gap)
            if best is None or value > best[0]:
                best = (value, cell)
        return best[1] if best is not None else None

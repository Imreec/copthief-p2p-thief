"""The reference's shipped heuristic, re-derived as arena opponents (M5-2; ADR-0002).

Interface-mirror of observed behavior (`domain/brains.py` @960499fd) — never reference
code. These are the DoD yardstick (PRD_police_brain §2): the role brains must take
≥ the configured win-rate off them. Both read OUR BeliefFilter's argmax (the
`most_likely()` analog) — perception held fixed, the disclosed harder-opponent choice.

Documented micro-deltas: distance ties break on our sorted move order (the reference
ties on its Direction-enum order — an implementation accident, not strategy); the
attributed barrier rate arrives via `options['ref_police_barrier_chance']` (the
reference's `barrier_chance = 0.15` class default) — config-owned, never a literal.
"""

from __future__ import annotations

from collections.abc import Mapping

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import STAY, Coord
from copthief_core.domain.rules import legal_moves
from copthief_core.strategy.brains import BrainBase, Observation
from copthief_core.strategy.decision import Decision


def _manhattan(a: Coord, b: Coord) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class RefThiefBrain(BrainBase):
    """Evade: maximize distance from the believed cop cell; prefer unvisited cells.

    The visited set is brain-local history (the reference reads its OwnGameState's) —
    fed from the observations this instance has decided on.
    """

    def __init__(self, *, seed: int, options: Mapping[str, float] | None = None) -> None:
        super().__init__(seed=seed, options=options)
        self._visited: set[Coord] = set()

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        self._visited.add(observation.position)
        threat = belief.argmax()
        candidates = sorted(
            legal_moves(observation.board, observation.position, observation.move_set)
        )
        if not candidates:
            return STAY

        def rank(move: str) -> tuple[int, bool]:
            dest = observation.board.apply_move(observation.position, move)
            return (_manhattan(dest, threat), dest not in self._visited)

        return max(candidates, key=rank)


class RefPoliceBrain(BrainBase):
    """Chase: minimize distance to the believed thief cell; sometimes wall the step-cell.

    The coin-flip barrier (seeded, rate from options) replaces the step it would have
    taken — the reference walls the cell of its best move instead of entering it.
    """

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        target = belief.argmax()
        candidates = sorted(
            legal_moves(observation.board, observation.position, observation.move_set)
        )
        if not candidates:
            return STAY
        return min(
            candidates,
            key=lambda m: _manhattan(observation.board.apply_move(observation.position, m), target),
        )

    def _decide(self, observation: Observation, belief: BeliefFilter) -> Decision:
        move = self._pick_move(observation, belief)
        chance = self._options.get("ref_police_barrier_chance", 0.0)
        quota_left = observation.barriers_used < observation.max_barriers
        if move != STAY and quota_left and self._rng.random() < chance:
            return Decision(barrier=observation.board.apply_move(observation.position, move))
        return Decision(move=move)

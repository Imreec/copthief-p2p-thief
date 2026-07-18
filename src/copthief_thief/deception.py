"""Self-mirror + deception timing (PRD_thief_brain §3): lie when they know AND can act.

The self-mirror is a second `BeliefFilter` — public API only, the M3-8 boundary
intact — fed exactly the evidence WE have transmitted (our scent grids). It meters
what a rational opponent can infer about us: SQ3's distrust stance, mirrored — they
can fake evidence at us; we can measure what our honest physics leaks.
"""

from __future__ import annotations

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import Board, Coord
from copthief_core.shared.config_model import PheromoneParams


class SelfMirror:
    """What the opponent can know about US, estimated from our own emissions."""

    def __init__(
        self,
        *,
        board: Board,
        move_set: tuple[str, ...],
        start: Coord,
        pheromones: PheromoneParams,
        smell_trust: float,
    ) -> None:
        self._filter = BeliefFilter(
            board=board,
            move_set=move_set,
            start=start,
            center_intensity=pheromones.center_intensity,
            decay=pheromones.decay,
            smell_trust=smell_trust,
            hint_trust=0.0,  # scent-only mirror: the strongest leak is the trail
        )

    def observe_turn(self, own_smell: dict[str, float]) -> None:
        """One opponent-side update: they model our move, then read our trail."""
        self._filter.predict()
        self._filter.update_scent(own_smell)

    def exposure(self, cell: Coord) -> float:
        """P(they place us at `cell`) under the mirrored pipeline."""
        return self._filter.prob_at(cell)


class DeceptionClock:
    """Budget + cooldown bookkeeping for the lie policy (one instance per game)."""

    def __init__(self, *, budget: int, cooldown: int) -> None:
        self._budget = budget
        self._cooldown = cooldown
        self._lies_used = 0
        self._last_lie_step: int | None = None

    def may_lie(self, step: int) -> bool:
        """True while the budget holds and the cooldown has elapsed."""
        if self._lies_used >= self._budget:
            return False
        if self._last_lie_step is not None and step - self._last_lie_step < self._cooldown:
            return False
        return True

    def record_lie(self, step: int) -> None:
        """Spend one lie."""
        self._lies_used += 1
        self._last_lie_step = step

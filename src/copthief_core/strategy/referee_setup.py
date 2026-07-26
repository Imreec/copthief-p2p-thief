"""Referee-mode fixture builders, split from strategy/referee (150-line rule, M5-3).

The belief and trail constructors both harnesses (referee game + belief eval) share:
signed pheromone params in, scent-only belief out (hints are a peer-mode feature).
"""

from __future__ import annotations

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import Coord
from copthief_core.domain.scent import ScentField
from copthief_core.domain.scent_models import ScentModel
from copthief_core.shared.config_model import Constitution


def referee_belief(
    constitution: Constitution,
    *,
    start: Coord,
    smell_trust: float,
    hint_trust: float = 0.0,
    scent_model: ScentModel | None = None,
) -> BeliefFilter:
    """A belief primed at the opponent's (scenario) start — scent-only by default;
    the M5-6 verbal referee passes a positive hint trust so hints reach the filter.
    `scent_model` selects the observation physics (M7-14); omitted, the reference
    form is built from the signed terms exactly as before."""
    return BeliefFilter(
        board=constitution.board.make_board(),
        move_set=constitution.movement.move_set,
        start=start,
        center_intensity=constitution.pheromones.center_intensity,
        decay=constitution.pheromones.decay,
        smell_trust=smell_trust,
        hint_trust=hint_trust,
        scent_model=scent_model,
    )


def referee_trail(constitution: Constitution, *, model: ScentModel | None = None) -> ScentField:
    """One mover's own scent field under the signed pheromone params; a passed
    `model` selects the emission physics (M7-14), mirroring the peer construction."""
    if model is not None:
        return ScentField(
            board_size=constitution.board.grid_size,
            origin=constitution.board.axis_start_index,
            model=model,
        )
    return ScentField(
        board_size=constitution.board.grid_size,
        window=constitution.pheromones.grid_size,
        decay=constitution.pheromones.decay,
        min_center_intensity=constitution.pheromones.min_center_intensity,
        origin=constitution.board.axis_start_index,
    )

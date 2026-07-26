"""Referee-mode Observation builders, split from strategy/referee (150-line rule, M7-14).

Pure assembly: each builder packs one side's legal view of the world — own truth plus
the signed alphabet, never the opponent's position (the Observation contract).
"""

from __future__ import annotations

from copthief_core.domain.board import Board, Coord
from copthief_core.domain.gazetteer import Gazetteer
from copthief_core.domain.scent import ScentField
from copthief_core.shared.config_model import Constitution
from copthief_core.strategy.brains import Observation


def thief_observation(
    constitution: Constitution,
    *,
    board: Board,
    position: Coord,
    step: int,
    trail: ScentField,
    gazetteer: Gazetteer | None,
) -> Observation:
    """The thief's view before its move (referee loop, first half of the turn)."""
    return Observation(
        board=board,
        position=position,
        move_set=constitution.movement.move_set,
        role="thief",
        step=step,
        survival_threshold=constitution.movement.survival_threshold,
        max_moves=constitution.movement.max_moves,
        gazetteer=gazetteer,
        own_smell=trail.snapshot(),
        pheromones=constitution.pheromones,
    )


def police_observation(
    constitution: Constitution,
    *,
    board: Board,
    position: Coord,
    step: int,
    trail: ScentField,
) -> Observation:
    """The cop's view before its action (referee loop, second half of the turn)."""
    return Observation(
        board=board,
        position=position,
        move_set=constitution.movement.move_set,
        role="police",
        step=step,
        barriers_used=len(board.barriers),
        max_barriers=constitution.movement.max_barriers,
        survival_threshold=constitution.movement.survival_threshold,
        max_moves=constitution.movement.max_moves,
        own_smell=trail.snapshot(),
        pheromones=constitution.pheromones,
    )

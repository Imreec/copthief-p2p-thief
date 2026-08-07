"""Belief-weighted distance, shared by any brain that reasons over a posterior.

Extracted when the best2934 arms (M7-45) needed it on both sides of the board: the
pursuer minimises it and the evader maximises it, and CLAUDE.md #11 forbids two
copies. Kept separate from `region` (pure geometry, no belief) because this one reads
the filter.
"""

from __future__ import annotations

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import Coord

__all__ = ["expected_distance"]


def expected_distance(cell: Coord, belief: BeliefFilter) -> float:
    """Posterior-weighted Manhattan distance from `cell` to the opponent.

    Input: a board cell and the belief filter over the opponent's position.
    Output: the expectation of |dr| + |dc| under the posterior, in cells.
    """
    return sum(
        p * (abs(cell[0] - spot[0]) + abs(cell[1] - spot[1])) for spot, p in belief.probs().items()
    )

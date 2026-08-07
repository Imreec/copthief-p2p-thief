"""uoh-sqak's opponent model + escape value (M7-46) — ⚑ thief repo, opponent model only.

Split out of `sqak_apex` at the 150-line rule, along the seam their own tree uses:
`strategy/opponent_model.py` + `strategy/archetypes.py` hold exactly this, and
`apex_cop.py` holds the search that consumes it.

Their cop scores a candidate position by how FREE the thief would be there — reachable
area, plus the gap to the cop, plus room from the walls — and takes the WORST case over
an ensemble of three archetype replies (`thief_v1` + `naive_edge` + `still`, unioned).
Area dominates: it reaches 49 where the other terms reach single digits, which is why
the cop reads as an area-strangler rather than a chaser.
"""

from __future__ import annotations

from copthief_core.domain.board import Board, Coord
from copthief_core.domain.rules import legal_moves
from copthief_core.strategy.region import region_size

__all__ = ["escape_value", "predicted_replies", "wall_distance", "worst_escape"]

# Their `thief_heuristic.ThiefBrain` weights, which the ensemble's first member runs.
_V1_EXITS = 0.3
_V1_RISK = 1.0


def wall_distance(board: Board, cell: Coord) -> int:
    """Their `endgame.wall_dist` — steps from `cell` to the nearest board edge."""
    low = board.axis_start_index
    high = low + board.grid_size - 1
    return min(cell[0] - low, high - cell[0], cell[1] - low, high - cell[1])


def _manhattan(a: Coord, b: Coord) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def escape_value(
    board: Board,
    cop: Coord,
    thief: Coord,
    move_set: tuple[str, ...],
    opts: dict[str, float],
) -> float:
    """Their `escape_value`: how free the thief is at `thief` with the cop at `cop`."""
    area = region_size(board, thief, move_set, int(opts["apex_region_cap"]), {})
    return (
        opts["apex_w_reach"] * area
        + opts["apex_w_dist"] * _manhattan(cop, thief)
        + opts["apex_w_wall"] * wall_distance(board, thief)
    )


def predicted_replies(
    board: Board, thief: Coord, cop: Coord, move_set: tuple[str, ...]
) -> set[Coord]:
    """Their `OpponentModel("ensemble")` — the UNION of three archetypes' replies.

    A union, not a vote: the caller maximises over it, so the cop plans against the most
    optimistic escape any of the three would take. `still` is the thief standing its
    ground, which is why `thief` itself is always a member.
    """
    targets = [board.apply_move(thief, m) for m in legal_moves(board, thief, move_set)]
    if not targets:
        return {thief}
    heuristic = max(
        targets,
        key=lambda t: (
            _manhattan(t, cop)
            + _V1_EXITS * sum(not board.is_blocked(n) for n in board.neighbors(t))
            - (_V1_RISK if _manhattan(t, cop) <= 1 else 0.0)
        ),
    )
    low = board.axis_start_index
    high = low + board.grid_size - 1
    corners = [(low, low), (low, high), (high, low), (high, high)]
    goal = max(corners, key=lambda c: _manhattan(c, cop))
    edge_runner = min(targets, key=lambda t: _manhattan(t, goal))
    return {heuristic, edge_runner, thief}


def worst_escape(
    board: Board,
    cop: Coord,
    thief: Coord,
    move_set: tuple[str, ...],
    opts: dict[str, float],
) -> float:
    """The value their search minimises: the best escape the ensemble could manage."""
    return max(
        escape_value(board, cop, reply, move_set, opts)
        for reply in predicted_replies(board, thief, cop, move_set)
    )

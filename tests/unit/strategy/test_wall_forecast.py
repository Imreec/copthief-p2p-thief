"""The one-ply worst-wall forecast + lethal gate (M9-3).

The barrier law limits placement to the cop's cell and its orthogonal
neighbors, so the trap game is exactly computable one ply ahead. Born from the
counted 30–90: our thief walked into (6,6) and sat while the two-wall seal
closed — a landing the forecast ranks last and the lethal gate refuses. The
belief-native form takes the elementwise MIN over the support cells: a kill
line through ANY plausible cop cell disqualifies the landing (a lone stale
argmax dodges phantom walls and walks into real ones).
"""

from copthief_core.domain.board import Board, Coord
from copthief_core.strategy.wall_forecast import lethal_landing, worst_wall_outcome

MOVE_SET = ("N", "S", "E", "W", "STAY")


def make_board(barriers: frozenset[Coord] = frozenset()) -> Board:
    return Board(grid_size=7, axis_origin_corner="top-left", axis_start_index=0, barriers=barriers)


def test_corner_landing_next_to_the_cop_is_lethal() -> None:
    """Cop support at (5,6): landing on (6,6) dies next turn (wall or step)."""
    assert lethal_landing(make_board(), (6, 6), [(5, 6)])


def test_landing_two_steps_away_is_not_lethal() -> None:
    """No support cell reaches (6,6) in one action from (4,6)."""
    assert not lethal_landing(make_board(), (6, 6), [(4, 6)])


def test_any_support_cell_with_a_kill_line_disqualifies() -> None:
    """Belief-native MIN: one far cell + one adjacent cell — still lethal."""
    assert lethal_landing(make_board(), (6, 6), [(0, 0), (6, 5)])


def test_worst_wall_shrinks_the_almost_sealed_pocket_to_nothing() -> None:
    """(5,6) already walled, cop at (6,4): the worst wall for a (6,6) landing is
    (6,5), leaving zero escapes and the one-cell region — the g01 death, seen
    one turn before it happened."""
    board = make_board(frozenset({(5, 6)}))
    escapes, region = worst_wall_outcome(board, (6, 6), (6, 4), MOVE_SET, region_cap=24)
    assert (escapes, region) == (0, 1)


def test_open_center_landing_survives_every_wall() -> None:
    """From (3,3) with the cop far, every hypothetical wall leaves escapes."""
    escapes, region = worst_wall_outcome(make_board(), (3, 3), (0, 0), MOVE_SET, region_cap=24)
    assert escapes >= 2
    assert region > 4


def test_exhausted_quota_forecasts_no_wall() -> None:
    """quota_left=0: the wall branch vanishes; only the step-on threat remains."""
    board = make_board(frozenset({(5, 6)}))
    escapes, region = worst_wall_outcome(
        board, (6, 6), (6, 4), MOVE_SET, region_cap=24, quota_left=0
    )
    assert escapes >= 1  # (6,5) stays open — no wall can close it

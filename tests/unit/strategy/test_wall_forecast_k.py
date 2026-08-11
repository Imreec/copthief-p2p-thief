"""M11-1 k-wall forecast — pockets invisible to the one-wall lookahead.

The M10 exposure (police-m10 vs doctrine-m10 32/32): a cage is built from
adjacency one tempo at a time, and the one-wall forecast prices only the FINAL
closing wall. `worst_walls_region` prices the whole investment: the worst
reachable region a stationary builder can leave a landing after up to k walls.
"""

from copthief_core.domain.board import Board
from copthief_core.strategy.wall_forecast import worst_walls_region

MOVE_SET = ("N", "S", "E", "W", "STAY")


def make_board(barriers: frozenset[tuple[int, int]] = frozenset()) -> Board:
    return Board(grid_size=7, axis_origin_corner="top-left", axis_start_index=0, barriers=barriers)


def test_zero_walls_is_the_plain_region() -> None:
    board = make_board()
    assert worst_walls_region(board, (0, 0), (1, 1), MOVE_SET, walls=0, reach=1) == 49


def test_one_wall_cannot_close_the_corner_pocket() -> None:
    # Cop at (1,1), landing at the (0,0) corner: either single wall — (0,1) or
    # (1,0) — leaves the other door open, so the corner still reads as open board.
    board = make_board()
    assert worst_walls_region(board, (0, 0), (1, 1), MOVE_SET, walls=1, reach=1) >= 40


def test_two_walls_seal_the_corner_pocket() -> None:
    # The two-wall truth the one-wall forecast cannot see: (0,1) + (1,0) — both in
    # the cop's stationary reach — leave the corner landing a region of exactly 1.
    board = make_board()
    assert worst_walls_region(board, (0, 0), (1, 1), MOVE_SET, walls=2, reach=1) == 1


def test_walls_beyond_the_reach_radius_are_not_credited() -> None:
    # A cop at (4,4) cannot seal the far corner with reach 1 — the forecast must
    # not invent walls the barrier law does not offer from there.
    board = make_board()
    assert worst_walls_region(board, (0, 0), (4, 4), MOVE_SET, walls=3, reach=1) >= 40


def test_reach_two_extends_the_builder_one_step() -> None:
    # Cop at (2,1): its stationary reach cannot touch (0,1)/(1,0) (both Manhattan
    # 2 away), but a one-step walk can — reach=2 credits the two-wall seal a
    # moving builder actually has.
    board = make_board()
    assert worst_walls_region(board, (0, 0), (2, 1), MOVE_SET, walls=2, reach=1) >= 40
    assert worst_walls_region(board, (0, 0), (2, 1), MOVE_SET, walls=2, reach=2) == 1


def test_quota_bounds_the_forecast() -> None:
    # With one wall left in the quota the two-wall seal is not a real threat.
    board = make_board()
    two = worst_walls_region(board, (0, 0), (1, 1), MOVE_SET, walls=2, reach=1)
    one = worst_walls_region(board, (0, 0), (1, 1), MOVE_SET, walls=1, reach=1)
    assert two == 1
    assert one >= 40

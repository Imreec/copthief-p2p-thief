"""NisYar1ThiefBrain (M11) — the flee-then-perch arm from the 08-11 g01 log."""

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import Board, Coord
from copthief_core.strategy.brains import Observation, make_brain
from copthief_core.strategy.nisyar1_thief import NisYar1ThiefBrain

MOVE_SET = ("N", "S", "E", "W", "STAY")


def make_board(barriers: frozenset[Coord] = frozenset()) -> Board:
    return Board(grid_size=7, axis_origin_corner="top-left", axis_start_index=0, barriers=barriers)


def make_belief(board: Board, cop_cell: Coord) -> BeliefFilter:
    return BeliefFilter(
        board=board,
        move_set=MOVE_SET,
        start=cop_cell,
        center_intensity=0.9,
        decay=0.1,
        smell_trust=0.0,
        hint_trust=0.0,
    )


def make_observation(board: Board, position: Coord) -> Observation:
    return Observation(
        board=board,
        position=position,
        move_set=MOVE_SET,
        role="thief",
        step=16,
        max_barriers=14,
        max_moves=35,
    )


def test_perches_at_the_logged_distance_two() -> None:
    """The g01 shape pinned exactly: at (0,4) with the cop believed at (2,4)
    (Manhattan 2) the log shows 21 consecutive STAYs — the perch holds."""
    board = make_board()
    brain = NisYar1ThiefBrain(seed=1)
    move = brain.pick_move(make_observation(board, (0, 4)), make_belief(board, (2, 4)))
    assert move == "STAY"


def test_wakes_and_flees_when_the_cop_closes() -> None:
    board = make_board()
    brain = NisYar1ThiefBrain(seed=1)
    move = brain.pick_move(make_observation(board, (0, 4)), make_belief(board, (1, 4)))
    dest = board.apply_move((0, 4), move)
    assert abs(dest[0] - 1) + abs(dest[1] - 4) >= 2  # distance restored


def test_registered_in_the_brain_factory() -> None:
    assert isinstance(make_brain("nisyar1-thief", seed=1), NisYar1ThiefBrain)

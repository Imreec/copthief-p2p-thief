"""NisYar1ThiefBrain (M11 part 2) — the runner arm from the 08-11 COUNTED logs.

The M11 flee-then-perch arm modeled their a0ba98d1 friendly; the counted ran
41b9fb76 and the perch is GONE (stays 20-25%, longest run 4, across g01/g03/g05).
These tests pin the refreshed runner shape: flee under pressure, rest only
briefly when safe, keep moving.
"""

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


def test_flees_while_the_cop_is_in_press_range() -> None:
    """Counted g02-class pressure: with the believed cop 2 away they MOVE
    (the friendly perch at Manhattan 2 no longer happens — 41b9fb76)."""
    board = make_board()
    brain = NisYar1ThiefBrain(seed=1)
    move = brain.pick_move(make_observation(board, (3, 4)), make_belief(board, (3, 2)))
    assert move != "STAY"
    dest = board.apply_move((3, 4), move)
    assert abs(dest[0] - 3) + abs(dest[1] - 2) >= 3  # distance grows


def test_rests_briefly_when_safe_but_never_perches() -> None:
    """Counted dwell shape: STAYs come in runs of <= 3 when the cop is far;
    the fourth consecutive turn always moves (longest observed run was 4
    including the wake turn; the 21-STAY perch is dead)."""
    board = make_board()
    brain = NisYar1ThiefBrain(seed=1)
    observation = make_observation(board, (5, 0))
    belief = make_belief(board, (0, 6))
    moves = [brain.pick_move(observation, belief) for _ in range(4)]
    assert moves[0] == "STAY"  # far cop: resting is allowed...
    assert "STAY" not in moves[3]  # ...but the dwell cap forces motion


def test_registered_in_the_brain_factory() -> None:
    assert isinstance(make_brain("nisyar1-thief", seed=1), NisYar1ThiefBrain)

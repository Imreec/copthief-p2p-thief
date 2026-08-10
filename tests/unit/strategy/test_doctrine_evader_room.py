"""DoctrineEvaderBrain room-first ordering (M10) — the anti-herding fix.

The 08-10 friendly's even games (g02/g04/g06) showed the M9 doctrine being HERDED:
with the cop's exact cell known (their every-turn claim collapsed our belief), the
hunted flight cap made "maximum distance" the ruling term, and maximum distance
from an advancing cop is monotonically the far corner — three identical corner
deaths at steps 13-16, one seal wall each. `room_first` demotes raw flight below
the worst-wall room terms once a small floor is met: keep barely-safe distance,
then keep the board OPEN — the shape of the opponent thief's central oscillation
that survived our own cop 3/3 in the same logs.
"""

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import Board, Coord
from copthief_core.strategy.brains import Observation
from copthief_core.strategy.doctrine_evader import DoctrineEvaderBrain

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
        step=7,
        barriers_used=0,
        max_barriers=14,
        max_moves=35,
    )


def _room_brain(seed: int = 3) -> DoctrineEvaderBrain:
    return DoctrineEvaderBrain(seed=seed, options={"room_first": 1.0})


def test_the_g02_herding_step_is_refused() -> None:
    """g02 step 7: us at (3,5), cop exactly known at (3,3) two west. The M9 doctrine
    took E — max flight — and was walked to the (6,6) corner; room-first keeps a
    four-escape destination instead of stepping toward the east wall."""
    board = make_board()
    move = _room_brain().pick_move(make_observation(board, (3, 5)), make_belief(board, (3, 3)))
    assert move != "E"
    dest = board.apply_move((3, 5), move)
    assert sum(1 for n in board.neighbors(dest) if not board.is_blocked(n)) == 4


def test_the_floor_still_refuses_closing_on_the_cop() -> None:
    """Room-first is not suicide: with the cop adjacent-diagonal, the move that
    maximizes room but lands in the cop's reach stays refused (lethal gate), and
    the survivor keeps distance at or above the floor."""
    board = make_board()
    move = _room_brain().pick_move(make_observation(board, (2, 2)), make_belief(board, (3, 3)))
    dest = board.apply_move((2, 2), move)
    assert abs(dest[0] - 3) + abs(dest[1] - 3) >= 2


def test_room_first_off_is_the_shipped_m9_ordering() -> None:
    """The knob defaults OFF: without it the g02 geometry still takes E — the M9
    champion's decision stream is untouched (champion-gate comparability)."""
    board = make_board()
    brain = DoctrineEvaderBrain(seed=3)
    move = brain.pick_move(make_observation(board, (3, 5)), make_belief(board, (3, 3)))
    assert move == "E"


def test_beyond_the_floor_farther_still_wins_ties() -> None:
    """Among equal-room landings the lifted flight cap still ranks farther higher —
    the demoted term is demoted, not deleted."""
    board = make_board()
    move = _room_brain().pick_move(make_observation(board, (3, 2)), make_belief(board, (3, 0)))
    dest = board.apply_move((3, 2), move)
    assert dest in {(3, 3), (2, 2), (4, 2)}
    assert dest[1] >= 2

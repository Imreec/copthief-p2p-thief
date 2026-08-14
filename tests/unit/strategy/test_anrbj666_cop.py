"""Anrbj666CopBrain (M11 part 2) — their FIELDED cop at HEAD 41e907d.

Pins the behaviors studied from the repos they shared (ADR-0011 consent basis,
re-implemented, no code copied): BFS chase, steady-heading interception,
trap walls with step-in preference / endgame wall-on-peak / contact-dwell
quota release, never-wall-out.
"""

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import Board, Coord
from copthief_core.strategy.anrbj666_cop import Anrbj666CopBrain, intercept_target
from copthief_core.strategy.brains import Observation, make_brain

MOVE_SET = ("N", "S", "E", "W", "STAY")


def make_board(barriers: frozenset[Coord] = frozenset()) -> Board:
    return Board(grid_size=7, axis_origin_corner="top-left", axis_start_index=0, barriers=barriers)


def make_belief(board: Board, prey_cell: Coord) -> BeliefFilter:
    return BeliefFilter(
        board=board,
        move_set=MOVE_SET,
        start=prey_cell,
        center_intensity=0.9,
        decay=0.1,
        smell_trust=0.0,
        hint_trust=0.0,
    )


def make_observation(board: Board, position: Coord, *, step: int, used: int = 0) -> Observation:
    return Observation(
        board=board,
        position=position,
        move_set=MOVE_SET,
        role="police",
        step=step,
        barriers_used=used,
        max_barriers=14,
        max_moves=35,
        survival_threshold=35,
    )


def test_intercept_meets_the_runner_never_follows() -> None:
    """A peak marching E along row 3 from (3,3): the cop at (1,5) can reach
    (3,5) in 2 steps, no later than the runner — that is the cut."""
    board = make_board()
    cut = intercept_target(board, (1, 5), (3, 3), (0, 1), MOVE_SET)
    assert cut == (3, 5)


def test_intercept_declines_when_no_cut_inside_the_horizon() -> None:
    board = make_board()
    assert intercept_target(board, (6, 0), (3, 3), (0, 1), MOVE_SET, horizon=1) is None


def test_prefers_the_step_in_capture_over_the_wall_mid_game() -> None:
    """Believed cell adjacent, mid-game, no dwell release: they step in
    (prefer_landing_capture), never spending the wall."""
    board = make_board()
    brain = Anrbj666CopBrain(seed=1)
    decision = brain.decide(make_observation(board, (0, 0), step=10), make_belief(board, (0, 1)))
    assert decision.barrier is None
    assert board.apply_move((0, 0), decision.move) == (0, 1)


def test_walls_the_peak_itself_in_the_last_two_turns() -> None:
    """remaining <= 2 kills the step-in preference: the rule-46 wall fires."""
    board = make_board()
    brain = Anrbj666CopBrain(seed=1)
    decision = brain.decide(make_observation(board, (0, 0), step=34), make_belief(board, (0, 1)))
    assert decision.barrier == (0, 1)


def test_cuts_the_reachable_escape_of_a_penned_peak() -> None:
    """Peak (0,2) has 3 escapes; the only one in our reach from (0,0) is (0,1),
    and walling it keeps the peak reachable (never-wall-out) — so it is cut."""
    board = make_board()
    brain = Anrbj666CopBrain(seed=1)
    decision = brain.decide(make_observation(board, (0, 0), step=10), make_belief(board, (0, 2)))
    assert decision.barrier == (0, 1)


def test_contact_dwell_releases_the_open_board_wall() -> None:
    """4 consecutive sharp turns at gap <= 2 open the cornered-ness gate:
    the 4-escape peak (3,5) gets its reachable escape (3,4) walled."""
    board = make_board()
    brain = Anrbj666CopBrain(seed=1)
    observation = make_observation(board, (3, 3), step=12)
    belief = make_belief(board, (3, 5))
    walls = [brain.decide(observation, belief).barrier for _ in range(4)]
    assert walls[:3] == [None, None, None]
    assert walls[3] == (3, 4)


def test_registered_in_the_brain_factory() -> None:
    assert isinstance(make_brain("anrbj666-police", seed=1), Anrbj666CopBrain)

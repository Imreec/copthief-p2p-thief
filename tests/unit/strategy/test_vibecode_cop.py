"""vibecode cop arm pins (M10 rebuild) — scripted opening, clean chase, one seal.

Pins the behaviors read off OUR OWN 2026-08-10 friendly logs
(`logs/imreeyal-vs-vibecode_g02/g04/g06.jsonl`, 43 sealed cop steps): the S,S,S
opening out of (0,0), a wall-AWARE chase that tracked our thief to Chebyshev 1 by
~step 10 in every game, and exactly ONE barrier per game — the corner-sealing
placement on the believed thief's low-escape cell ((0,5) in g04/g06, (6,5) in
g02). The pre-08-10 model (east-wall habit, wall-blind dithering, wasted
placements) is DEAD; these pins replace those.
"""

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import Board, Coord
from copthief_core.strategy.brains import Observation
from copthief_core.strategy.vibecode_cop import VibecodeCopBrain

MOVE_SET = ("N", "S", "E", "W", "STAY")


def make_board(barriers: frozenset[Coord] = frozenset()) -> Board:
    return Board(grid_size=7, axis_origin_corner="top-left", axis_start_index=0, barriers=barriers)


def make_belief(board: Board, thief_cell: Coord) -> BeliefFilter:
    return BeliefFilter(
        board=board,
        move_set=MOVE_SET,
        start=thief_cell,
        center_intensity=0.9,
        decay=0.1,
        smell_trust=0.0,
        hint_trust=0.0,
    )


def make_observation(
    board: Board, position: Coord, *, step: int = 10, barriers_used: int = 0
) -> Observation:
    return Observation(
        board=board,
        position=position,
        move_set=MOVE_SET,
        role="police",
        step=step,
        barriers_used=barriers_used,
        max_barriers=14,
        max_moves=35,
    )


def test_the_opening_is_three_scripted_south_steps() -> None:
    """g02/g04/g06 steps 1-3: S,S,S out of the (0,0) spawn, all three games."""
    board = make_board()
    brain = VibecodeCopBrain(seed=1)
    position = (0, 0)
    for step in (1, 2, 3):
        decision = brain.decide(
            make_observation(board, position, step=step), make_belief(board, (3, 3))
        )
        assert decision.move == "S"
        assert decision.barrier is None
        position = board.apply_move(position, decision.move)
    assert position == (3, 0)


def test_the_chase_routes_around_walls() -> None:
    """The 08-10 cop never dithered against a wall (unlike the dead 2026-08 model):
    with the direct east lane barriered the chase detours instead of bouncing."""
    board = make_board(frozenset({(3, 1)}))
    brain = VibecodeCopBrain(seed=1)
    decision = brain.decide(make_observation(board, (3, 0)), make_belief(board, (3, 3)))
    assert decision.barrier is None
    assert decision.move in ("N", "S")


def test_the_corner_seal_is_the_g04_wall() -> None:
    """g04/g06 step 13: cop at (1,5), thief believed at the (0,6) corner — the one
    barrier of the game lands on (0,5), the corner's open west escape."""
    board = make_board()
    brain = VibecodeCopBrain(seed=1)
    decision = brain.decide(make_observation(board, (1, 5)), make_belief(board, (0, 6)))
    assert decision.barrier == (0, 5)
    assert decision.move == "STAY"


def test_exactly_one_wall_per_game() -> None:
    """13 of 43 logged cop steps were wall-eligible chases past the seal; none
    placed a second barrier — the arm stops walling once its one wall is spent."""
    board = make_board(frozenset({(0, 5)}))
    brain = VibecodeCopBrain(seed=1)
    decision = brain.decide(
        make_observation(board, (1, 5), barriers_used=1), make_belief(board, (0, 6))
    )
    assert decision.barrier is None


def test_an_open_center_target_draws_no_wall() -> None:
    """The cop never walled the central loop in g02/g04/g06 openings — a 4-escape
    believed cell is chased, not sealed."""
    board = make_board()
    brain = VibecodeCopBrain(seed=1)
    decision = brain.decide(make_observation(board, (3, 2)), make_belief(board, (3, 3)))
    assert decision.barrier is None

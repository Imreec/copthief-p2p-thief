"""NisYar1CopBrain (M11 part 2) — the counted cage cop, its own module at last.

Pins the 41b9fb76 shape measured in reports/counted-series/imreeyal/ g02/g04/g06
(6 walls per game, every one an escape-cut adjacent to our lag-1 cell, 27/33
closing moves) and corroborated by anrbj666's independent mimic of the same cop
(approach to gap 2, hold, first wall at step 9, fewest-exit seals).
"""

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import Board, Coord
from copthief_core.strategy.brains import Observation, make_brain
from copthief_core.strategy.nisyar1_cop import NisYar1CopBrain

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
    )


def test_chases_the_believed_cell_when_far() -> None:
    board = make_board()
    brain = NisYar1CopBrain(seed=1)
    decision = brain.decide(make_observation(board, (0, 0), step=4), make_belief(board, (5, 5)))
    assert decision.barrier is None
    dest = board.apply_move((0, 0), decision.move)
    assert abs(dest[0] - 5) + abs(dest[1] - 5) == 9  # strictly closes


def test_holds_the_metronome_gap_before_the_wall_phase() -> None:
    """Their measured invariant: at gap <= 2 before step 9 the cop STAYS
    (never closes to 1) and places nothing."""
    board = make_board()
    brain = NisYar1CopBrain(seed=1)
    decision = brain.decide(make_observation(board, (3, 3), step=5), make_belief(board, (3, 5)))
    assert decision.move == "STAY"
    assert decision.barrier is None


def test_walls_the_shared_corner_cell_in_diagonal_contact() -> None:
    """Counted g02 step 18 exactly: cop (3,3), believed thief (4,2) — the wall
    lands on (3,2), the sorted-first of the two shared-adjacent cells. All six
    counted walls follow this rule (verified against g02/g04/g06)."""
    board = make_board()
    brain = NisYar1CopBrain(seed=1)
    decision = brain.decide(make_observation(board, (3, 3), step=18), make_belief(board, (4, 2)))
    assert decision.barrier == (3, 2)


def test_no_wall_before_step_nine_even_in_diagonal_contact() -> None:
    board = make_board()
    brain = NisYar1CopBrain(seed=1)
    decision = brain.decide(make_observation(board, (3, 3), step=8), make_belief(board, (4, 2)))
    assert decision.barrier is None


def test_respects_its_observed_wall_budget() -> None:
    """They spent exactly 6 walls per counted game; the 7th is never placed."""
    board = make_board()
    brain = NisYar1CopBrain(seed=1)
    decision = brain.decide(
        make_observation(board, (3, 3), step=20, used=6), make_belief(board, (4, 2))
    )
    assert decision.barrier is None


def test_registered_in_the_brain_factory() -> None:
    assert isinstance(make_brain("nisyar1-police", seed=1), NisYar1CopBrain)

"""Action legality, barrier rule, imprisonment, capture, end conditions (book ch.3 §3.4–3.5)."""

from copthief_core.domain.board import Board, Coord
from copthief_core.domain.rules import (
    Outcome,
    check_end,
    is_imprisoned,
    is_legal_barrier,
    is_legal_move,
    legal_moves,
)

MOVE_SET = ("N", "S", "E", "W", "STAY")


def _board(size: int = 7, barriers: frozenset[Coord] = frozenset()) -> Board:
    return Board(
        grid_size=size, axis_origin_corner="top-left", axis_start_index=0, barriers=barriers
    )


def test_all_five_moves_legal_from_an_open_center_cell() -> None:
    assert set(legal_moves(_board(), (3, 3), MOVE_SET)) == set(MOVE_SET)


def test_moves_off_the_board_edge_are_illegal() -> None:
    moves = legal_moves(_board(), (0, 0), MOVE_SET)
    assert "N" not in moves
    assert "W" not in moves
    assert {"S", "E", "STAY"} <= set(moves)


def test_move_into_a_barrier_is_illegal() -> None:
    board = _board(barriers=frozenset({(2, 3)}))
    assert not is_legal_move(board, (3, 3), "N", MOVE_SET)
    assert is_legal_move(board, (3, 3), "S", MOVE_SET)


def test_move_outside_the_signed_move_set_is_illegal() -> None:
    assert not is_legal_move(_board(), (3, 3), "NE", MOVE_SET)
    assert not is_legal_move(_board(), (3, 3), "STAY", ("N", "S", "E", "W"))


def test_barrier_legal_on_cop_cell_and_orthogonal_neighbors_only() -> None:
    board = _board()
    assert is_legal_barrier(board, (3, 3), (3, 3), barriers_used=0, max_barriers=14)
    assert is_legal_barrier(board, (3, 3), (2, 3), barriers_used=0, max_barriers=14)
    assert not is_legal_barrier(board, (3, 3), (2, 2), barriers_used=0, max_barriers=14)
    assert not is_legal_barrier(board, (3, 3), (5, 3), barriers_used=0, max_barriers=14)


def test_barrier_quota_and_double_placement_are_refused() -> None:
    board = _board(barriers=frozenset({(2, 3)}))
    assert not is_legal_barrier(board, (3, 3), (2, 3), barriers_used=1, max_barriers=14)
    assert not is_legal_barrier(board, (3, 3), (3, 4), barriers_used=14, max_barriers=14)


def test_barrier_off_the_board_is_refused() -> None:
    assert not is_legal_barrier(_board(), (0, 0), (-1, 0), barriers_used=0, max_barriers=14)


def test_thief_walled_into_a_corner_is_imprisoned() -> None:
    board = _board(barriers=frozenset({(0, 1), (1, 0)}))
    assert is_imprisoned(board, (0, 0))


def test_thief_with_one_open_neighbor_is_not_imprisoned() -> None:
    board = _board(barriers=frozenset({(0, 1)}))
    assert not is_imprisoned(board, (0, 0))


def test_full_ring_imprisons_even_though_stay_is_possible() -> None:
    ring = frozenset({(2, 3), (4, 3), (3, 2), (3, 4)})
    assert is_imprisoned(_board(barriers=ring), (3, 3))


def test_cop_landing_on_thief_ends_in_capture() -> None:
    outcome = check_end(
        _board(),
        cop_pos=(3, 3),
        thief_pos=(3, 3),
        steps_survived=5,
        survival_threshold=35,
        max_moves=35,
    )
    assert outcome is Outcome.COP_CAPTURE


def test_barrier_dropped_on_thief_cell_ends_in_capture() -> None:
    board = _board(barriers=frozenset({(3, 3)}))
    outcome = check_end(
        board,
        cop_pos=(3, 4),
        thief_pos=(3, 3),
        steps_survived=5,
        survival_threshold=35,
        max_moves=35,
    )
    assert outcome is Outcome.COP_CAPTURE


def test_imprisoned_thief_counts_as_captured() -> None:
    ring = frozenset({(2, 3), (4, 3), (3, 2), (3, 4)})
    outcome = check_end(
        _board(barriers=ring),
        cop_pos=(0, 0),
        thief_pos=(3, 3),
        steps_survived=5,
        survival_threshold=35,
        max_moves=35,
    )
    assert outcome is Outcome.COP_CAPTURE


def test_thief_reaching_the_survival_threshold_wins() -> None:
    outcome = check_end(
        _board(),
        cop_pos=(0, 0),
        thief_pos=(3, 3),
        steps_survived=35,
        survival_threshold=35,
        max_moves=35,
    )
    assert outcome is Outcome.THIEF_SURVIVAL


def test_step_cap_without_capture_is_survival() -> None:
    outcome = check_end(
        _board(),
        cop_pos=(0, 0),
        thief_pos=(3, 3),
        steps_survived=40,
        survival_threshold=99,
        max_moves=40,
    )
    assert outcome is Outcome.THIEF_SURVIVAL


def test_midgame_position_has_no_outcome_yet() -> None:
    outcome = check_end(
        _board(),
        cop_pos=(0, 0),
        thief_pos=(3, 3),
        steps_survived=5,
        survival_threshold=35,
        max_moves=35,
    )
    assert outcome is None


def test_capture_takes_precedence_over_simultaneous_survival() -> None:
    outcome = check_end(
        _board(),
        cop_pos=(3, 3),
        thief_pos=(3, 3),
        steps_survived=35,
        survival_threshold=35,
        max_moves=35,
    )
    assert outcome is Outcome.COP_CAPTURE

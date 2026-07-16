"""Board geometry: bounds, axis semantics, move deltas, barriers (book ch.3; PRD_engine E-1/E-3)."""

import pytest

from copthief_core.domain.board import Board, Coord


def _board(
    size: int = 7,
    origin: str = "top-left",
    start: int = 0,
    barriers: frozenset[Coord] = frozenset(),
) -> Board:
    return Board(
        grid_size=size, axis_origin_corner=origin, axis_start_index=start, barriers=barriers
    )


def test_in_bounds_covers_exactly_the_grid_range() -> None:
    board = _board(size=7)
    assert board.in_bounds((0, 0))
    assert board.in_bounds((6, 6))
    assert not board.in_bounds((-1, 0))
    assert not board.in_bounds((0, 7))


def test_axis_start_index_shifts_the_valid_range() -> None:
    board = _board(size=7, start=1)
    assert not board.in_bounds((0, 0))
    assert board.in_bounds((1, 1))
    assert board.in_bounds((7, 7))
    assert not board.in_bounds((8, 1))


def test_north_decreases_row_when_origin_is_top_left() -> None:
    board = _board(origin="top-left")
    assert board.apply_move((3, 3), "N") == (2, 3)
    assert board.apply_move((3, 3), "S") == (4, 3)
    assert board.apply_move((3, 3), "E") == (3, 4)
    assert board.apply_move((3, 3), "W") == (3, 2)


def test_vertical_axis_flips_when_origin_is_a_bottom_corner() -> None:
    board = _board(origin="bottom-left")
    assert board.apply_move((3, 3), "N") == (4, 3)
    assert board.apply_move((3, 3), "E") == (3, 4)


def test_horizontal_axis_flips_when_origin_is_a_right_corner() -> None:
    board = _board(origin="top-right")
    assert board.apply_move((3, 3), "E") == (3, 2)
    assert board.apply_move((3, 3), "N") == (2, 3)


def test_stay_keeps_the_agent_in_place() -> None:
    assert _board().apply_move((3, 3), "STAY") == (3, 3)


def test_unknown_move_raises() -> None:
    with pytest.raises(ValueError, match="unknown move"):
        _board().apply_move((3, 3), "NE")


def test_barrier_blocks_a_cell_and_out_of_bounds_counts_as_blocked() -> None:
    board = _board(barriers=frozenset({(1, 1)}))
    assert board.is_blocked((1, 1))
    assert board.is_blocked((-1, 0))
    assert not board.is_blocked((0, 0))


def test_with_barrier_is_immutable_and_cumulative() -> None:
    board = _board()
    walled = board.with_barrier((2, 2)).with_barrier((3, 2))
    assert not board.is_blocked((2, 2))
    assert walled.is_blocked((2, 2))
    assert walled.is_blocked((3, 2))


def test_neighbors_are_in_bounds_orthogonal_cells_only() -> None:
    board = _board(size=7)
    assert set(board.neighbors((0, 0))) == {(1, 0), (0, 1)}
    assert set(board.neighbors((3, 3))) == {(2, 3), (4, 3), (3, 2), (3, 4)}

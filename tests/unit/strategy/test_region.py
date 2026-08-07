def test_path_length_routes_around_a_wall() -> None:
    """A barrier on the straight line lengthens the path rather than blocking it."""
    from copthief_core.domain.board import Board
    from copthief_core.strategy.region import path_length

    board = Board(grid_size=7, axis_origin_corner="top-left", axis_start_index=0)
    moves = ("N", "S", "E", "W", "STAY")
    assert path_length(board, (0, 0), (0, 2), moves) == 2
    assert path_length(board.with_barrier((0, 1)), (0, 0), (0, 2), moves) == 4


def test_path_length_is_none_when_the_target_is_sealed_off() -> None:
    """A fully walled-in target is unreachable, which is what lets a cop reject a
    wall that would cut it off from the thief."""
    from copthief_core.domain.board import Board
    from copthief_core.strategy.region import path_length

    board = Board(grid_size=7, axis_origin_corner="top-left", axis_start_index=0)
    for cell in ((0, 1), (1, 0)):
        board = board.with_barrier(cell)
    assert path_length(board, (3, 3), (0, 0), ("N", "S", "E", "W", "STAY")) is None

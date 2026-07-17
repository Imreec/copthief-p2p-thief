"""M1 skeleton policy: deterministic seeded geometric play, always legal."""

from copthief_core.domain.board import Board
from copthief_core.domain.rules import is_legal_move
from copthief_core.peer.policy import SkeletonPolicy

MOVE_SET = ("N", "S", "E", "W", "STAY")


def _board() -> Board:
    return Board(grid_size=7, axis_origin_corner="top-left", axis_start_index=0)


def test_same_seed_gives_the_same_walk() -> None:
    a, b = SkeletonPolicy(seed=17), SkeletonPolicy(seed=17)
    board = _board()
    pos_a = pos_b = (3, 3)
    for _ in range(20):
        move_a, move_b = a.pick_move(board, pos_a, MOVE_SET), b.pick_move(board, pos_b, MOVE_SET)
        assert move_a == move_b
        pos_a, pos_b = board.apply_move(pos_a, move_a), board.apply_move(pos_b, move_b)


def test_every_picked_move_is_legal_even_from_a_corner() -> None:
    policy = SkeletonPolicy(seed=3)
    board = _board()
    pos = (0, 0)
    for _ in range(50):
        move = policy.pick_move(board, pos, MOVE_SET)
        assert is_legal_move(board, pos, move, MOVE_SET)
        pos = board.apply_move(pos, move)


def test_hints_cycle_through_the_template_bank_within_word_cap() -> None:
    policy = SkeletonPolicy(seed=0)
    hints = [policy.next_hint(hint_max_words=15) for _ in range(6)]
    assert all(len(h.split()) <= 15 for h in hints)
    assert len(set(hints)) > 1  # the bank cycles, not one frozen string

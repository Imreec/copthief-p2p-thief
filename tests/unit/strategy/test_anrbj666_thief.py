"""Anrbj666ThiefBrain (M11 part 2) — their FIELDED thief at HEAD f95b438.

Pins the behaviors studied from the repos they shared (ADR-0011 consent basis,
re-implemented, no code copied): room-outranks-range while blind (imprisonment
is capture), the 0.75 trusted flip to adjacency-avoiding wall-forecast play,
and the fresh-trail flip back to capped flight.
"""

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import Board, Coord
from copthief_core.strategy.anrbj666_thief import Anrbj666ThiefBrain
from copthief_core.strategy.brains import Observation, make_brain

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
        survival_threshold=35,
    )


def test_blind_room_outranks_range_in_the_corner() -> None:
    """Their 8feb6ad fix (nis-yar1 killed them 3x in the (6,6) pocket): blind,
    a 3-exit cell beats the 2-exit corner even stepping no farther — and W
    wins over N on the distance tie-break."""
    board = make_board()
    brain = Anrbj666ThiefBrain(seed=1, options={"trust_mass": 2.0})
    move = brain.pick_move(make_observation(board, (6, 6)), make_belief(board, (1, 6)))
    assert move == "W"


def test_trusted_play_never_lands_adjacent_while_quota_remains() -> None:
    """At peak mass >= 0.75 the exact-info key rules: min(d,2) bans adjacency
    (any landing in the cop's wall reach is a rule-46 death)."""
    board = make_board()
    brain = Anrbj666ThiefBrain(seed=1)
    move = brain.pick_move(make_observation(board, (3, 3)), make_belief(board, (3, 5)))
    dest = board.apply_move((3, 3), move)
    assert abs(dest[0] - 3) + abs(dest[1] - 5) >= 2


def test_fresh_trail_flips_room_back_to_flight() -> None:
    """Blind + believed cop within 4: capped distance replaces the room term
    (their fresh_flee), so the 2-exit east pocket outranks the roomier south."""
    board = make_board(frozenset({(1, 4), (1, 5), (1, 6)}))
    fresh = Anrbj666ThiefBrain(seed=1, options={"trust_mass": 2.0})
    move = fresh.pick_move(make_observation(board, (0, 3)), make_belief(board, (1, 1)))
    assert move == "E"


def test_without_fresh_trail_room_still_rules() -> None:
    """Room mode refuses the 2-exit east pocket; among the 3-exit options STAY
    is farthest from the believed cop and STAY wins ties — their exact shape."""
    board = make_board(frozenset({(1, 4), (1, 5), (1, 6)}))
    roomy = Anrbj666ThiefBrain(seed=1, options={"trust_mass": 2.0, "fresh_radius": 0.0})
    move = roomy.pick_move(make_observation(board, (0, 3)), make_belief(board, (1, 1)))
    assert move == "STAY"


def test_registered_in_the_brain_factory() -> None:
    assert isinstance(make_brain("anrbj666-thief", seed=1), Anrbj666ThiefBrain)

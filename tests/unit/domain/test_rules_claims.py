"""Claim-gated landing capture (PRD_claims §2.4, §5.1; M7-19).

Book scoring table 2 (PDF p.38) defines the capture end-event as the cop landing on the
thief's cell **and declaring** a Capture Claim. So a cop that lands and stays silent
forfeits that capture — self-punishing, not illegal, which is what makes claim frequency
a strategy knob at all.

The other two capture forms (PRD_engine E-4 — a barrier on the thief's cell, and
imprisonment) are produced by barrier placement, whose declaration the book makes
UNCONDITIONAL one sentence earlier ("every barrier placement... may not be placed in
secret"). They are therefore never claim-gated: a quiet cop keeps its whole trap game.
"""

from copthief_core.domain.board import Board
from copthief_core.domain.rules import Outcome, check_end

THRESHOLD = 35


def _board(barriers: frozenset[tuple[int, int]] = frozenset()) -> Board:
    return Board(grid_size=7, axis_origin_corner="top-left", axis_start_index=0, barriers=barriers)


def _end(board: Board, *, cop: tuple[int, int], thief: tuple[int, int], **kwargs: bool) -> object:
    return check_end(
        board,
        cop_pos=cop,
        thief_pos=thief,
        steps_survived=5,
        survival_threshold=THRESHOLD,
        max_moves=THRESHOLD,
        **kwargs,
    )


def test_an_unclaimed_landing_is_not_a_capture_and_the_game_continues() -> None:
    assert _end(_board(), cop=(3, 3), thief=(3, 3), claim_standing=False) is None


def test_a_claimed_landing_is_still_a_capture() -> None:
    assert _end(_board(), cop=(3, 3), thief=(3, 3), claim_standing=True) is Outcome.COP_CAPTURE


def test_the_gate_defaults_open_so_legacy_callers_are_unchanged() -> None:
    assert _end(_board(), cop=(3, 3), thief=(3, 3)) is Outcome.COP_CAPTURE


def test_a_barrier_on_the_thief_captures_even_while_the_cop_is_silent() -> None:
    board = _board(barriers=frozenset({(3, 3)}))
    assert _end(board, cop=(3, 4), thief=(3, 3), claim_standing=False) is Outcome.COP_CAPTURE


def test_imprisonment_captures_even_while_the_cop_is_silent() -> None:
    ring = frozenset({(2, 3), (4, 3), (3, 2), (3, 4)})
    assert _end(_board(ring), cop=(0, 0), thief=(3, 3), claim_standing=False) is Outcome.COP_CAPTURE


def test_a_silent_cop_standing_on_an_imprisoned_thief_still_captures() -> None:
    # Both forms coincide: the landing is gated away, imprisonment still ends it.
    ring = frozenset({(2, 3), (4, 3), (3, 2), (3, 4)})
    assert _end(_board(ring), cop=(3, 3), thief=(3, 3), claim_standing=False) is Outcome.COP_CAPTURE


def test_survival_still_resolves_under_a_silent_cop() -> None:
    outcome = check_end(
        _board(),
        cop_pos=(3, 3),
        thief_pos=(3, 3),
        steps_survived=THRESHOLD,
        survival_threshold=THRESHOLD,
        max_moves=THRESHOLD,
        claim_standing=False,
    )
    assert outcome is Outcome.THIEF_SURVIVAL

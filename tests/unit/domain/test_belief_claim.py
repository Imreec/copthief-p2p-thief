"""Certainty-grade capture claims in the belief filter (PRD_claims §4.1; M7-18).

A capture claim is a plaintext pre-reveal of a cell already sealed in the same message's
commit, and the book sanctions a false one with the game (App E rules 21-22, PDF p.145).
That puts it in the same evidence class as a DECLARED BARRIER — which this filter already
treats as certain — and not in the scent class, whose never-eliminate invariant (SQ3)
exists because grids are unauthenticated. So a claim collapses the distribution.

Role-blind by construction: the filter tracks "the opponent", whichever side we are.
"""

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import Board

MOVE_SET = ("N", "S", "E", "W", "STAY")


def make_filter(
    *,
    start: tuple[int, int] = (3, 3),
    barriers: frozenset[tuple[int, int]] = frozenset(),
) -> BeliefFilter:
    board = Board(grid_size=7, axis_origin_corner="top-left", axis_start_index=0, barriers=barriers)
    return BeliefFilter(
        board=board,
        move_set=MOVE_SET,
        start=start,
        center_intensity=0.9,
        decay=0.1,
        smell_trust=4.0,
        hint_trust=1.0,
    )


def test_a_claim_collapses_the_distribution_onto_the_claimed_cell() -> None:
    belief = make_filter(start=(3, 3))
    belief.predict()  # a spread-out prior, as after any opponent turn
    assert len(belief.probs()) > 1
    belief.note_claim((1, 5))
    assert belief.probs() == {(1, 5): 1.0}
    assert belief.argmax() == (1, 5)
    assert belief.belief_error((1, 5)) == 0.0


def test_a_claim_outside_the_current_support_still_collapses() -> None:
    # The claim is truth and our prior was simply wrong — the filter must follow the
    # evidence rather than defend its own estimate.
    belief = make_filter(start=(3, 3))
    far = (6, 0)
    assert belief.prob_at(far) == 0.0
    belief.note_claim(far)
    assert belief.probs() == {far: 1.0}
    assert sum(belief.probs().values()) == 1.0


def test_predict_after_a_claim_spreads_over_exactly_that_cells_legal_moves() -> None:
    # Certainty is not permanent: the very next opponent turn re-spreads it, and the
    # spread honours declared barriers exactly as it does from any other support.
    blocked = (2, 3)
    belief = make_filter(start=(0, 0), barriers=frozenset({blocked}))
    belief.note_claim((3, 3))
    belief.predict()
    probs = belief.probs()
    assert belief.prob_at(blocked) == 0.0
    assert len(probs) == 4  # N is walled off; S, E, W, STAY remain
    assert all(value == 0.25 for value in probs.values())
    assert sum(probs.values()) == 1.0

"""Scent/hint likelihood updates (PRD_belief §2.3–2.4) + the last-known baseline (§3).

The locked model gives received intensities an age reading (each missing 0.1 of
intensity ≈ one turn older, subtractive form) — fresh evidence collapses the belief,
aged evidence widens it, and NO grid can ever eliminate the true cell (SQ3: grids are
unauthenticated and freely fakeable).
"""

import pytest

from copthief_core.domain.belief import BeliefFilter, LastKnownTracker
from copthief_core.domain.board import Board

MOVE_SET = ("N", "S", "E", "W", "STAY")
FRESH = 0.8  # center_intensity 0.9 - one decay 0.1 (PRD_scent §2 example)


def make_filter(*, start: tuple[int, int] = (3, 3), smell_trust: float = 4.0) -> BeliefFilter:
    board = Board(grid_size=7, axis_origin_corner="top-left", axis_start_index=0)
    return BeliefFilter(
        board=board,
        move_set=MOVE_SET,
        start=start,
        center_intensity=0.9,
        decay=0.1,
        smell_trust=smell_trust,
        hint_trust=1.0,
    )


def test_fresh_center_scent_collapses_belief_onto_the_emitter() -> None:
    belief = make_filter(start=(3, 3))
    belief.predict()  # five equal cells
    belief.update_scent({"3,4": FRESH})
    assert belief.argmax() == (3, 4)
    # Trust 4.0: the fresh cell's 1+4*0.8 likelihood takes 4.2/8.2 of the mass.
    assert belief.prob_at((3, 4)) == pytest.approx(4.2 / 8.2)


def test_aged_scent_widens_the_plausible_set_with_its_implied_age() -> None:
    fresh_belief, aged_belief = make_filter(), make_filter()
    for belief in (fresh_belief, aged_belief):
        for _ in range(3):
            belief.predict()
    fresh_belief.update_scent({"3,3": FRESH})  # age 0: they are HERE
    aged_belief.update_scent({"3,3": 0.6})  # age 2: they were here two turns ago
    fresh_top = fresh_belief.prob_at(fresh_belief.argmax())
    aged_top = aged_belief.prob_at(aged_belief.argmax())
    assert fresh_top > aged_top  # aged evidence is spread over the age-ball
    # Manhattan-2 cells share the aged boost that the fresh update denies them.
    assert aged_belief.prob_at((2, 4)) > fresh_belief.prob_at((2, 4))


def test_fabricated_far_field_scent_never_eliminates_the_true_cell() -> None:
    belief = make_filter(start=(3, 3))
    belief.predict()
    belief.update_scent({"6,6": FRESH, "6,5": FRESH, "5,6": FRESH})  # a fabricated blob
    for cell in [(3, 3), (2, 3), (4, 3), (3, 2), (3, 4)]:
        assert belief.prob_at(cell) > 0.0  # shifted, never zeroed
    assert sum(belief.probs().values()) == pytest.approx(1.0)


def test_empty_grid_leaves_the_belief_unchanged() -> None:
    belief = make_filter(start=(3, 3))
    belief.predict()
    before = belief.probs()
    belief.update_scent({})
    assert belief.probs() == pytest.approx(before)


def test_zero_trust_makes_scent_a_no_op() -> None:
    belief = make_filter(smell_trust=0.0)
    belief.predict()
    before = belief.probs()
    belief.update_scent({"3,4": FRESH})
    assert belief.probs() == pytest.approx(before)


def test_hint_seam_multiplies_and_renormalizes() -> None:
    belief = make_filter(start=(3, 3))
    belief.predict()
    belief.update_hint([(3, 4), (2, 3)], 1.0)  # gazetteer cells at weight 1 -> doubled
    assert belief.prob_at((3, 4)) == pytest.approx(2.0 / 7.0)
    assert belief.prob_at((3, 3)) == pytest.approx(1.0 / 7.0)
    assert sum(belief.probs().values()) == pytest.approx(1.0)


def test_hint_outside_the_support_shifts_nothing_but_never_creates_mass() -> None:
    belief = make_filter(start=(3, 3))
    belief.update_hint([(0, 0)], 5.0)  # start delta: hint cell has zero prior mass
    assert belief.prob_at((3, 3)) == pytest.approx(1.0)
    assert belief.prob_at((0, 0)) == 0.0


# --- the §3 baseline ---------------------------------------------------------------
# "Certainly placed" means protocol-grade evidence only: the signed start, or a proven
# claim outcome. Scent grids are unauthenticated (SQ3) — a naive tracker treating a
# fresh center as truth would be trivially spoofable, so the baseline never reads them.


def test_last_known_tracker_is_a_point_mass_at_the_signed_start() -> None:
    board = Board(grid_size=7, axis_origin_corner="top-left", axis_start_index=0)
    tracker = LastKnownTracker(board=board, start=(3, 3))
    assert tracker.belief_error((3, 3)) == pytest.approx(0.0)
    assert tracker.belief_error((3, 4)) == pytest.approx(1.0)
    assert tracker.argmax() == (3, 3)


def test_last_known_tracker_ignores_scent_but_follows_certain_evidence() -> None:
    board = Board(grid_size=7, axis_origin_corner="top-left", axis_start_index=0)
    tracker = LastKnownTracker(board=board, start=(3, 3))
    tracker.predict()  # turns passing never move the last-known point
    tracker.update_scent({"3,4": FRESH})  # unauthenticated: not certain placement
    assert tracker.argmax() == (3, 3)
    tracker.update_certain((5, 5))  # protocol-grade evidence (e.g. a proven claim)
    assert tracker.argmax() == (5, 5)
    assert tracker.belief_error((5, 5)) == pytest.approx(0.0)


def test_last_known_tracker_without_any_evidence_is_uniform() -> None:
    board = Board(grid_size=7, axis_origin_corner="top-left", axis_start_index=0)
    tracker = LastKnownTracker(board=board, start=None)
    assert tracker.belief_error((3, 3)) == pytest.approx(1.0 - 1.0 / 49.0)
    assert tracker.belief_error((0, 0)) == pytest.approx(1.0 - 1.0 / 49.0)

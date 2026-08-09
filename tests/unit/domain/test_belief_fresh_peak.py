"""The fresh-peak scent decode (M9-2) — the sharp observation tier, re-landed.

Under `subtractive_chebyshev_v1` a just-laid centre transmits the unique
post-decay stamp (`emit - decay`, the model's `fresh_center`); no other cell
in a legal field can carry it (rings are lower, older centres have decayed).
The M7-46 experiment proved the decode itself trivially sharp (0.063 -> 0.98)
and REVERTED it because the 2-ply search converted certainty into passivity;
the M9-1 solver removes that failure mode, so the tier returns — config-gated,
off by default, never eliminating (SQ3: a fabricated peak must degrade the
estimate, not zero the truth).
"""

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.belief_observation import fresh_peak_scores
from copthief_core.domain.board import Board
from copthief_core.domain.scent_models import SubtractiveChebyshevV1

MOVE_SET = ("N", "S", "E", "W", "STAY")

MODEL = SubtractiveChebyshevV1(
    {
        "field_size": 5,
        "emit_intensity": 0.9,
        "min_center_intensity": 0.05,
        "decay_per_step": 0.1,
        "rounding_decimals": 3,
    }
)


def make_board() -> Board:
    return Board(grid_size=7, axis_origin_corner="top-left", axis_start_index=0)


def make_filter(*, fresh_peak_trust: float) -> BeliefFilter:
    return BeliefFilter(
        board=make_board(),
        move_set=MOVE_SET,
        start=(3, 3),
        center_intensity=0.9,
        decay=0.1,
        smell_trust=4.0,
        hint_trust=0.0,
        scent_model=MODEL,
        fresh_peak_trust=fresh_peak_trust,
    )


def test_the_unique_stamp_names_the_emitter_cell() -> None:
    """One cell at `fresh_center` (0.8): score 1.0 there, 0.0 everywhere else."""
    grid = {"3,4": 0.8, "3,3": 0.5, "2,4": 0.5, "4,4": 0.5, "3,5": 0.2}
    support = [(3, 3), (3, 4), (2, 4)]
    scores = fresh_peak_scores(grid, support, MODEL.age_of)
    assert scores == {(3, 3): 0.0, (3, 4): 1.0, (2, 4): 0.0}


def test_an_ambiguous_frame_abstains() -> None:
    """Two age-zero cells (a frame legal physics cannot produce): no decode."""
    grid = {"3,4": 0.8, "5,5": 0.8}
    assert fresh_peak_scores(grid, [(3, 4), (5, 5)], MODEL.age_of) == {}


def test_a_stale_frame_abstains() -> None:
    """No age-zero cell at all (opponent's trail fully decayed): no decode."""
    grid = {"3,4": 0.6, "3,5": 0.3}
    assert fresh_peak_scores(grid, [(3, 4)], MODEL.age_of) == {}


def test_enabled_filter_collapses_onto_the_peak() -> None:
    """The re-landed M7-46 behavior: after a spread, one fresh frame makes the
    peak cell dominate the posterior (>0.9) — the sharpness the solver feeds on."""
    belief = make_filter(fresh_peak_trust=199.0)
    belief.predict()
    belief.predict()
    belief.update_scent({"3,4": 0.8, "3,3": 0.5, "2,4": 0.5, "4,4": 0.5})
    assert belief.prob_at((3, 4)) > 0.9


def test_never_eliminates_the_rest_of_the_support() -> None:
    """SQ3: the peak boosts, it does not zero — every prior support cell keeps
    strictly positive mass, so a fabricated stamp stays recoverable."""
    belief = make_filter(fresh_peak_trust=199.0)
    belief.predict()
    support_before = set(belief.probs())
    belief.update_scent({"3,4": 0.8})
    after = belief.probs()
    assert all(after.get(cell, 0.0) > 0.0 for cell in support_before)


def test_disabled_by_default_is_byte_identical_to_the_voucher_path() -> None:
    """`fresh_peak_trust=0` (the shipped default): the M3-3 voucher path,
    probability-for-probability — the measurement-preserving contract."""
    grid = {"3,4": 0.8, "3,3": 0.5}
    enabled_off = make_filter(fresh_peak_trust=0.0)
    control = BeliefFilter(
        board=make_board(),
        move_set=MOVE_SET,
        start=(3, 3),
        center_intensity=0.9,
        decay=0.1,
        smell_trust=4.0,
        hint_trust=0.0,
        scent_model=MODEL,
    )
    for belief in (enabled_off, control):
        belief.predict()
        belief.update_scent(grid)
    assert enabled_off.probs() == control.probs()

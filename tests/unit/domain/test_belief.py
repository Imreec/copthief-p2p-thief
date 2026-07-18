"""BeliefFilter core (PRD_belief §2): prior, barrier-aware predict, normalization, guard.

The filter is exact — plain float sums over the board's cells — so every test here can
assert probability identities directly (mass ≈ 1, support = motion-reachable set).
"""

import pytest

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import Board

MOVE_SET = ("N", "S", "E", "W", "STAY")


def make_filter(
    *,
    start: tuple[int, int] = (3, 3),
    barriers: frozenset[tuple[int, int]] = frozenset(),
    smell_trust: float = 4.0,
) -> BeliefFilter:
    board = Board(grid_size=7, axis_origin_corner="top-left", axis_start_index=0, barriers=barriers)
    return BeliefFilter(
        board=board,
        move_set=MOVE_SET,
        start=start,
        center_intensity=0.9,
        decay=0.1,
        smell_trust=smell_trust,
        hint_trust=1.0,
    )


def _mass(belief: BeliefFilter) -> float:
    return sum(belief.probs().values())


def test_prior_is_a_delta_at_the_signed_start() -> None:
    belief = make_filter(start=(3, 3))
    assert belief.prob_at((3, 3)) == 1.0
    assert belief.probs() == {(3, 3): 1.0}
    assert belief.argmax() == (3, 3)


def test_predict_spreads_uniformly_over_legal_actions() -> None:
    belief = make_filter(start=(3, 3))
    belief.predict()
    # Interior cell: 4 moves + STAY, uniform fifths.
    assert belief.prob_at((3, 3)) == pytest.approx(0.2)
    for cell in [(2, 3), (4, 3), (3, 2), (3, 4)]:
        assert belief.prob_at(cell) == pytest.approx(0.2)
    assert _mass(belief) == pytest.approx(1.0)


def test_predict_conserves_mass_at_edges_and_corners() -> None:
    belief = make_filter(start=(0, 0))
    for _ in range(5):
        belief.predict()
        assert _mass(belief) == pytest.approx(1.0)


def test_barriers_block_diffusion() -> None:
    belief = make_filter(start=(3, 3), barriers=frozenset({(2, 3)}))
    belief.predict()
    assert belief.prob_at((2, 3)) == 0.0
    # 3 remaining moves + STAY: uniform quarters.
    assert belief.prob_at((3, 3)) == pytest.approx(0.25)
    assert _mass(belief) == pytest.approx(1.0)


def test_note_barrier_constrains_later_predicts() -> None:
    belief = make_filter(start=(3, 3))
    belief.note_barrier((2, 3))
    belief.predict()
    assert belief.prob_at((2, 3)) == 0.0
    assert _mass(belief) == pytest.approx(1.0)


def test_support_never_includes_negative_probabilities() -> None:
    belief = make_filter()
    for _ in range(10):
        belief.predict()
        belief.update_scent({"1,1": 0.4})
        assert all(p > 0.0 for p in belief.probs().values())
        assert _mass(belief) == pytest.approx(1.0)


def test_argmax_tie_breaks_deterministically() -> None:
    belief = make_filter(start=(3, 3))
    belief.predict()  # five equal cells -> smallest coordinate wins, reproducibly
    assert belief.argmax() == (2, 3)


def test_degenerate_evidence_resets_to_the_reachable_prior() -> None:
    belief = make_filter(start=(3, 3))
    belief.predict()
    reachable = set(belief.probs())
    # A -1.0-weight hint over the WHOLE support is contradictory fabricated evidence:
    # the posterior mass collapses to 0 and the guard must reset, never NaN/crash.
    belief.update_hint(list(reachable), -1.0)
    assert _mass(belief) == pytest.approx(1.0)
    assert set(belief.probs()) == reachable  # uniform over the motion-reachable set
    assert belief.prob_at((3, 3)) == pytest.approx(1.0 / len(reachable))


def test_belief_error_is_one_minus_truth_probability() -> None:
    belief = make_filter(start=(3, 3))
    assert belief.belief_error((3, 3)) == pytest.approx(0.0)
    belief.predict()
    assert belief.belief_error((3, 3)) == pytest.approx(0.8)
    assert belief.belief_error((0, 6)) == pytest.approx(1.0)

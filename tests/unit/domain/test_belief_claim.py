"""Capture claims in the belief filter (M7-18, re-scoped by the M11-2 red-team).

A claim collapses the distribution ONLY when it is kinematically possible. The
M7-18 unconditional collapse leaned on "a false claim costs the game (rules
21-22)" — verified vacuous in the M11 red-team: no audit path anywhere compares
per-turn claims to the revealed track, and the 08-10 vibecode logs (42/43
speculative claims, both audits Verified OK) show the league treats speculative
claims as legal probes. So a claim naming a cell the opponent could not possibly
occupy is free adversarial input, not evidence — refused, counted, and the
posterior stands. A plausible claim keeps its M7-18 barrier-class certainty:
for every truthful claimer the gate is a no-op by construction, because a true
cell is always inside the motion envelope.
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


def test_a_plausible_claim_collapses_the_distribution_onto_the_claimed_cell() -> None:
    belief = make_filter(start=(3, 3))
    belief.predict()  # a spread-out prior, as after any opponent turn
    assert len(belief.probs()) > 1
    belief.note_claim((2, 3))  # one legal step from the start: inside the envelope
    assert belief.probs() == {(2, 3): 1.0}
    assert belief.argmax() == (2, 3)
    assert belief.belief_error((2, 3)) == 0.0


def test_an_impossible_claim_is_refused_and_counted() -> None:
    # Zero opponent turns have elapsed: the opponent IS at its signed start. A claim
    # naming the far corner is physically impossible — the M11-2 gate refuses it.
    belief = make_filter(start=(3, 3))
    prior = belief.probs()
    belief.note_claim((6, 0))
    assert belief.probs() == prior
    assert belief.claim_refusals == 1


def test_a_plausible_claim_outside_the_support_still_collapses() -> None:
    # The prior can be WRONG (a lying hint hard-excluded the truth) while the claim
    # is possible — the filter follows the evidence rather than defend its estimate.
    belief = make_filter(start=(3, 3))
    belief.predict()
    excluded = (2, 3)
    belief.update_hint([excluded], weight=-1.0)
    assert belief.prob_at(excluded) == 0.0
    belief.note_claim(excluded)
    assert belief.probs() == {excluded: 1.0}
    assert sum(belief.probs().values()) == 1.0


def test_the_envelope_grows_one_legal_step_per_predict() -> None:
    belief = make_filter(start=(3, 3))
    for _ in range(2):
        belief.predict()
    belief.note_claim((3, 5))  # Manhattan 2 in 2 turns: possible
    assert belief.probs() == {(3, 5): 1.0}
    belief.note_claim((3, 0))  # Manhattan 3 after only those 2 turns: impossible
    assert belief.probs() == {(3, 5): 1.0}
    assert belief.claim_refusals == 1


def test_a_claim_on_a_barriered_cell_is_refused() -> None:
    blocked = (3, 4)
    belief = make_filter(start=(3, 3))
    belief.predict()
    belief.note_barrier(blocked)
    belief.note_claim(blocked)
    assert belief.prob_at(blocked) == 0.0
    assert belief.claim_refusals == 1


def test_predict_after_a_claim_spreads_over_exactly_that_cells_legal_moves() -> None:
    # Certainty is not permanent: the very next opponent turn re-spreads it, and the
    # spread honours declared barriers exactly as it does from any other support.
    blocked = (2, 3)
    belief = make_filter(start=(3, 4), barriers=frozenset({blocked}))
    belief.predict()
    belief.note_claim((3, 3))  # adjacent to the start: plausible
    belief.predict()
    probs = belief.probs()
    assert belief.prob_at(blocked) == 0.0
    assert len(probs) == 4  # N is walled off; S, E, W, STAY remain
    assert all(value == 0.25 for value in probs.values())
    assert sum(probs.values()) == 1.0

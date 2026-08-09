"""Outbound barrier path (M5-2; PRD_police_brain §3/§7): the police WALLS on the wire.

First wire-visible new behavior since M3: `barrier_placed` (schema-mirrored since M1-5,
F9-validated inbound) now rides outbound when the brain's Decision is a barrier. The
sealed record stays self-consistent — move `"BARRIER"`, position unchanged, the state
string carries the grown barrier list — and SQ2 holds: no capture_claim on a non-MOVE.
"""

from dataclasses import replace
from pathlib import Path

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.crypto import verify
from copthief_core.peer.session import PeerSession
from copthief_core.shared.config import load_all
from copthief_core.strategy.brains import BrainBase, Observation
from copthief_core.strategy.decision import Decision

CONSTITUTION, _LIVE_PRIVATE, _LIMITS = load_all(Path("config"), counted=False)
# The move-turns-still-claim pin tests the mechanism; the M9-5 confidence gate is
# held open here and pinned on its own in test_claims.py.
PRIVATE = replace(
    _LIVE_PRIVATE,
    police_options={**_LIVE_PRIVATE.police_options, "claim_threshold": 0.0},
)


class _Waller(BrainBase):
    """Proposes a barrier on the cell east of the cop, forever."""

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        return "E"

    def _decide(self, observation: Observation, belief: BeliefFilter) -> Decision:
        east = observation.board.apply_move(observation.position, "E")
        return Decision(barrier=east)


def _police_session() -> PeerSession:
    return PeerSession(CONSTITUTION, PRIVATE, role="police", seed=5)


def test_barrier_turn_rides_the_wire_and_seals_self_consistently() -> None:
    session = _police_session()
    session.brain = _Waller(seed=5)
    before = session.position
    message = session.take_turn(now=0.0)
    east = session.board.apply_move(before, "E")
    assert message["barrier_placed"] == list(east)
    assert message["capture_claim"] is None  # SQ2: claims ride MOVE turns only
    assert session.position == before  # a barrier turn moves nothing
    assert east in session.board.barriers  # our own legality respects our own wall
    sealed = session.records[-1]
    assert sealed.payload["move"] == "BARRIER"
    assert sealed.payload["position"] == list(before)
    assert str(list(east)) in sealed.payload["state"]  # the state string grew the wall
    assert verify(sealed.payload, sealed.nonce, sealed.commit)


def test_our_barrier_constrains_the_opponent_belief_motion_model() -> None:
    session = _police_session()
    session.brain = _Waller(seed=5)
    session.take_turn(now=0.0)
    east = session.board.apply_move(session.position, "E")
    assert session.belief.prob_at(east) == 0.0  # occupancy excluded, motion constrained


def test_quota_exhaustion_degrades_the_wall_to_a_legal_move() -> None:
    session = _police_session()
    session.brain = _Waller(seed=5)
    session.barriers_placed = CONSTITUTION.movement.max_barriers  # quota already spent
    exhausted = session.take_turn(now=0.0)
    assert exhausted["barrier_placed"] is None
    assert session.records[-1].payload["move"] == "E"  # the waller's fallback, legal


def test_move_turns_still_claim_and_carry_no_barrier() -> None:
    session = _police_session()  # config-selected brain: a mover, not a waller
    message = session.take_turn(now=0.0)
    assert message["barrier_placed"] is None
    if session.records[-1].payload["move"] != "STAY":
        assert message["capture_claim"] == list(session.position)

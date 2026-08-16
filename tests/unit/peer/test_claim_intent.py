"""M13 claim intent (ADR-0016): the claim gate rides the brain's hunted posterior.

The best2934 counted forfeits (g02 s16, g04/g06 s12): the M12 intercept steered the
landing onto the thief's true cell, but the gate re-read the RAW belief (0.0049 there,
0.990 one cell behind) and stayed silent on a winning claim. The brain's own confidence
in its landing — when it offers one (`Decision.landing_confidence`) — is the gate's
input; the raw belief is only the fallback for brains that do not price their landings.

Split from test_claims.py (150-line rule); the mechanism pins stay there.
"""

from dataclasses import replace
from pathlib import Path

from copthief_core.domain.state_machine import GameState
from copthief_core.peer.session import PeerSession
from copthief_core.shared.config import load_all
from copthief_core.strategy.decision import Decision

CONSTITUTION, _LIVE_PRIVATE, _LIMITS = load_all(Path("config"), counted=False)


class _ConfidentBrain:
    """Decision stub carrying an explicit landing confidence (the M12 intercept case)."""

    def __init__(self, move: str, confidence: float | None) -> None:
        self._move, self._confidence = move, confidence

    def decide(self, observation, belief) -> "Decision":  # noqa: ANN001 - test stub
        return Decision(move=self._move, landing_confidence=self._confidence)


def _police_with_threshold(threshold: float) -> PeerSession:
    private = replace(
        _LIVE_PRIVATE,
        police_options={**_LIVE_PRIVATE.police_options, "claim_threshold": threshold},
    )
    police = PeerSession(CONSTITUTION, private, role="police", seed=1)
    thief = PeerSession(CONSTITUTION, private, role="thief", seed=2)
    thief.handle_negotiate(police.negotiate_payload())
    police.handle_negotiate(thief.negotiate_payload())
    police.machine.state = GameState.COMPUTING_MOVE
    return police


def _landing_cell(session: PeerSession, move: str) -> tuple[int, int]:
    return session.board.apply_move(session.position, move)


def test_the_brains_landing_confidence_outranks_the_raw_belief() -> None:
    police = _police_with_threshold(0.1)
    police.brain = _ConfidentBrain("S", 0.9)
    # The raw belief still sits on the signed start — nowhere near our landing cell.
    assert police.belief.prob_at(_landing_cell(police, "S")) < 0.1
    message = police.take_turn(now=1.0)
    assert message["capture_claim"] == list(police.position)


def test_a_low_priced_landing_stays_silent_whatever_the_raw_belief_says() -> None:
    police = _police_with_threshold(0.1)
    for _ in range(12):  # grow the M11-2 motion envelope so the collapse is plausible
        police.belief.predict()
    police.belief.note_claim(_landing_cell(police, "S"))  # raw belief: certain there
    police.brain = _ConfidentBrain("S", 0.05)
    assert police.take_turn(now=1.0)["capture_claim"] is None


def test_a_brain_that_prices_nothing_falls_back_to_the_raw_belief() -> None:
    police = _police_with_threshold(0.9)
    for _ in range(12):
        police.belief.predict()
    police.belief.note_claim(_landing_cell(police, "S"))
    police.brain = _ConfidentBrain("S", None)
    assert police.take_turn(now=1.0)["capture_claim"] == list(police.position)

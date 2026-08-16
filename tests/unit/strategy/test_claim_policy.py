"""The cop's claim decision as a pure policy (PRD_claims §5.1; M7-19).

Claim frequency is unregulated (the book mandates truthfulness and the thief's response
duty, never a cadence — PRD_claims §2), so when to declare is a strategy knob. This is
that knob, isolated from the referee loop: given what the cop just did and how likely it
thinks a capture is, would it declare?

`threshold=None` means claim CONFIDENCE is not modeled — the always-claim emitter. M13
(ADR-0016): even that emitter claims only landings; a STAY/BARRIER turn has nothing to
declare on any wire. `0.0` is the faithful model of the fielded emitter's cadence
(`peer/turns.py`, mirroring the reference `turn_sender.py`).
"""

from copthief_core.strategy.referee_claims import ClaimPolicy


def test_an_unmodelled_policy_claims_every_landing_and_nothing_else() -> None:
    # M13 wire-true (ADR-0016): even the always-claim emitter has nothing to declare
    # on a STAY or BARRIER turn — a claim needs a landing on any wire.
    policy = ClaimPolicy()
    assert not policy.modeled
    assert policy.claims(barrier_placed=False, move="N", confidence=0.0)
    assert not policy.claims(barrier_placed=False, move="STAY", confidence=1.0)
    assert not policy.claims(barrier_placed=True, move="BARRIER", confidence=1.0)


def test_threshold_zero_reproduces_todays_emitter() -> None:
    policy = ClaimPolicy(threshold=0.0)
    assert policy.modeled
    assert policy.claims(barrier_placed=False, move="N", confidence=0.0)
    assert not policy.claims(barrier_placed=False, move="STAY", confidence=1.0)
    assert not policy.claims(barrier_placed=True, move="BARRIER", confidence=1.0)


def test_a_moving_cop_below_the_threshold_stays_quiet() -> None:
    policy = ClaimPolicy(threshold=0.5)
    assert not policy.claims(barrier_placed=False, move="N", confidence=0.49)
    assert policy.claims(barrier_placed=False, move="N", confidence=0.5)
    assert policy.claims(barrier_placed=False, move="N", confidence=0.9)


def test_an_unreachable_threshold_silences_the_cop_entirely() -> None:
    policy = ClaimPolicy(threshold=2.0)  # confidence is a probability, so never met
    assert not policy.claims(barrier_placed=False, move="N", confidence=1.0)

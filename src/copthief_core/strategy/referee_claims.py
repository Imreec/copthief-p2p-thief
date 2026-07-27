"""The cop's capture-claim policy (PRD_claims §5.1; M7-19).

Claim FREQUENCY is unregulated. The book mandates that a claim be truthful (App E rules
21-22) and that the thief answer one honestly (p.38 iron rules), but never how often to
declare — and one sentence after the capture clause it *does* mandate declaring every
barrier placement, so the omission is a drafting choice, not an oversight (PRD_claims §2).

What silence costs is priced by the book itself: scoring table 2 defines the capture
end-event as the cop landing on the thief's cell **and declaring** it. A silent cop
forfeits that landing. Self-punishing, not illegal — which is exactly what makes this a
strategy knob rather than a rules question.

Pure: no I/O, no clock, no RNG. The referee loop owns the game state; this owns only the
decision, so the same policy can be swept without touching the loop.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["ClaimPolicy"]

# The emitter never claims on these (peer/turns.py, mirroring reference turn_sender.py):
# a cop that walls or stays has not landed anywhere, so it has nothing to declare.
_NON_LANDING_MOVE = "STAY"


@dataclass(frozen=True)
class ClaimPolicy:
    """When the cop declares (Input: what it just did + its own capture confidence;
    Output: whether a claim stands this turn).

    `threshold=None` means claims are NOT modelled: every same-cell ending resolves, which
    is the historical referee physics every committed arena table was measured under.
    Any float switches the model on, and `0.0` is then the faithful model of TODAY's
    emitter — declare on every moving turn, never on STAY or BARRIER.
    """

    threshold: float | None = None

    @property
    def modeled(self) -> bool:
        """True when this policy models the claim channel at all."""
        return self.threshold is not None

    def claims(self, *, barrier_placed: bool, move: str, confidence: float) -> bool:
        """Would the cop declare on this turn?

        `confidence` is the cop's own P(thief is on the cell I just landed on), read from
        its belief — so a threshold buys silence exactly when a capture looks unlikely,
        and pays for it by forfeiting the landings its belief was wrong about.
        """
        if self.threshold is None:
            return True
        if barrier_placed or move == _NON_LANDING_MOVE:
            return False
        return confidence >= self.threshold

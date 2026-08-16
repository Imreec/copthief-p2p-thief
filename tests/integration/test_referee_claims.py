"""Claim-gated capture through the whole referee loop (PRD_claims §5.1; M7-19).

The book's scoring table makes the landing capture conditional on the cop declaring it,
so once claiming is a choice the referee cannot resolve every same-cell ending. M13
(ADR-0016) pinned the wire's actual grading: a claim is graded ONCE, at the thief's
receive, against its post-move cell (empirical 19/19 across all counted claim/response
pairs) — so the landing form lives on the cop's half-turn only, and a thief stepping
onto the cop afterwards is graded by nothing. The old both-halves gating was the
instrument's generosity; the counted series kept refuting it.

The M7-19 lesson still stands as a passing test: a cop that never declares never
converts a collision, however sure we would like to be.
"""

from pathlib import Path

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.rules import Outcome
from copthief_core.shared.config import load_all
from copthief_core.strategy.brains import BrainBase, Observation
from copthief_core.strategy.decision import Decision
from copthief_core.strategy.referee import play_referee_game
from copthief_core.strategy.referee_claims import ClaimPolicy

CONSTITUTION, PRIVATE, _LIMITS = load_all(Path("config"), counted=False)

COP_CELL = (3, 3)
THIEF_CELL = (3, 4)  # due east of the cop; "W" walks the thief onto it


class _SitterBrain(BrainBase):
    """Never moves — a cop that only ever STAYs never declares once claims are modelled."""

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        return "STAY"


class _WestWalkerBrain(BrainBase):
    """Walks west once, then sits — scripts the thief onto the cop's cell."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self._walked = False

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        if self._walked:
            return "STAY"
        self._walked = True
        return "W"


class _EastWalkerBrain(BrainBase):
    """Walks east once, then sits — scripts the cop onto the thief's cell."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self._walked = False

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        if self._walked:
            return "STAY"
        self._walked = True
        return "E"


def _play(police: BrainBase, thief: BrainBase, policy: ClaimPolicy | None) -> Outcome:
    return play_referee_game(
        CONSTITUTION,
        police_brain=police,
        thief_brain=thief,
        smell_trust=PRIVATE.smell_trust_weight,
        seed=1,
        cop_start=COP_CELL,
        thief_start=THIEF_CELL,
        claim_policy=policy,
    ).outcome


def test_a_thief_initiated_collision_never_converts_even_unmodelled() -> None:
    # M13 wire-true (ADR-0016): a claim is graded ONCE, at the thief's receive, against
    # its post-move cell (empirical 19/19 across all counted claim/response pairs). A
    # thief stepping onto the cop afterwards is graded by nothing — the old thief-half
    # conversion here was the instrument's generosity, never the wire's.
    outcome = _play(_SitterBrain(seed=1), _WestWalkerBrain(seed=2), None)
    assert outcome is Outcome.THIEF_SURVIVAL


class _FarWestWalkerBrain(BrainBase):
    """Walks west twice, then sits — scripts the thief onto a cell the cop just claimed."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self._steps = 0

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        self._steps += 1
        return "W" if self._steps <= 2 else "STAY"


def test_a_stale_claim_does_not_convert_the_thiefs_next_walk_in() -> None:
    # M13 wire-true (ADR-0016): cop (3,3) steps E to (3,4) and claims it while the
    # thief is still at (3,5) — graded false at receive. The thief then walks onto
    # (3,4). No code path on the wire grades that second collision.
    outcome = play_referee_game(
        CONSTITUTION,
        police_brain=_EastWalkerBrain(seed=1),
        thief_brain=_FarWestWalkerBrain(seed=2),
        smell_trust=PRIVATE.smell_trust_weight,
        seed=1,
        cop_start=COP_CELL,
        thief_start=(3, 6),
        claim_policy=ClaimPolicy(threshold=0.0),
    ).outcome
    assert outcome is Outcome.THIEF_SURVIVAL


def test_a_cop_that_never_declares_never_converts_a_collision() -> None:
    # THE g06 CASE. The thief walks onto a cop that only STAYs, so no claim is ever
    # standing — the collision is real and the capture is forfeit. Pinned, not excused.
    outcome = _play(_SitterBrain(seed=1), _WestWalkerBrain(seed=2), ClaimPolicy(threshold=0.0))
    assert outcome is Outcome.THIEF_SURVIVAL


def test_a_standing_claim_converts_a_collision_the_thief_walked_into() -> None:
    # The cop moves (and so declares) one turn; the thief then steps onto that cell.
    # The claim from the cop's own last turn is what makes it a capture.
    outcome = _play(_EastWalkerBrain(seed=1), _SitterBrain(seed=2), ClaimPolicy(threshold=0.0))
    assert outcome is Outcome.COP_CAPTURE


def test_a_moving_cop_below_its_threshold_forfeits_the_landing() -> None:
    outcome = _play(_EastWalkerBrain(seed=1), _SitterBrain(seed=2), ClaimPolicy(threshold=2.0))
    assert outcome is Outcome.THIEF_SURVIVAL


class _WallerBrain(BrainBase):
    """Walls the cell due east of itself on its first turn — capture by barrier."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self._walled = False

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        return "STAY"

    def _decide(self, observation: Observation, belief: BeliefFilter) -> Decision:
        if self._walled:
            return Decision(move="STAY")
        self._walled = True
        return Decision(barrier=THIEF_CELL)


def test_the_barrier_capture_form_survives_a_totally_silent_cop() -> None:
    # A quiet cop keeps its whole trap game. This cop never declares anything (it never
    # even moves), and still captures — the book requires barrier placements be declared
    # unconditionally, so that form is not the cop's to withhold.
    outcome = _play(_WallerBrain(seed=1), _SitterBrain(seed=2), ClaimPolicy(threshold=2.0))
    assert outcome is Outcome.COP_CAPTURE

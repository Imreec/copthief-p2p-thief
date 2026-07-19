"""Hint-intent seam (M5-3 core prerequisite; PRD_thief_brain §3): the brain decides
WHEN to lie — the M3-4 mechanism finally gets its policy input.

A Decision may carry `hint_verdict` (+ a chosen decoy `hint_landmark`); peer/turns
composes the wire hint accordingly and seals the intent truthfully (lying in hints is
legal play; lying in sealed state is forfeit). Brains that say nothing keep the
truthful default byte-for-byte. The Observation now also carries what a deception
policy needs: the gazetteer, our own transmitted scent so far, and the signed
pheromone params (the self-mirror's construction kit).
"""

from pathlib import Path

from copthief_core.domain.belief import BeliefFilter
from copthief_core.peer.session import PeerSession
from copthief_core.shared.config import load_all, load_gazetteer
from copthief_core.strategy.brains import BrainBase, Observation
from copthief_core.strategy.decision import Decision
from copthief_core.strategy.hints import VERDICT_LIE, VERDICT_TRUTH, compose_hint

CONSTITUTION, PRIVATE, _LIMITS = load_all(Path("config"), counted=False)
GAZETTEER = load_gazetteer(
    Path("config") / "gazetteer.json",
    map_area=CONSTITUTION.world.map_area,
    board=CONSTITUTION.board.make_board(),
)


class _LiarBrain(BrainBase):
    """Always lies toward a fixed decoy landmark (policy stub for the seam test)."""

    def __init__(self, decoy: str) -> None:
        super().__init__(seed=0)
        self._decoy = decoy

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        return "STAY"

    def _decide(self, observation: Observation, belief: BeliefFilter) -> Decision:
        return Decision(move="STAY", hint_verdict=VERDICT_LIE, hint_landmark=self._decoy)


class _SpyBrain(BrainBase):
    """Records the observation it was shown (pins the new Observation fields)."""

    def __init__(self) -> None:
        super().__init__(seed=0)
        self.seen: list[Observation] = []

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        self.seen.append(observation)
        return "STAY"


def _thief_session() -> PeerSession:
    return PeerSession(CONSTITUTION, PRIVATE, role="thief", seed=9, gazetteer=GAZETTEER)


def test_compose_hint_accepts_an_explicit_decoy_landmark() -> None:
    decoy = GAZETTEER.farthest((0, 0))
    hint = compose_hint(
        GAZETTEER,
        position=(0, 0),
        max_words=CONSTITUTION.world.hint_max_words,
        salt=0,
        verdict=VERDICT_LIE,
        landmark=decoy,
    )
    assert hint.landmark == decoy
    assert hint.verdict == VERDICT_LIE
    assert GAZETTEER.parse(hint.text, max_words=CONSTITUTION.world.hint_max_words) == decoy


def test_compose_hint_falls_back_when_the_landmark_is_unknown() -> None:
    hint = compose_hint(
        GAZETTEER,
        position=(0, 0),
        max_words=CONSTITUTION.world.hint_max_words,
        salt=0,
        verdict=VERDICT_LIE,
        landmark="Atlantis",
    )
    assert hint.landmark in GAZETTEER.landmarks()  # never fabricate off-vocabulary text


def test_a_lying_decision_reaches_the_wire_and_seals_its_intent() -> None:
    session = _thief_session()
    decoy = GAZETTEER.landmarks()[-1]
    session.brain = _LiarBrain(decoy)
    message = session.take_turn(now=0.0)
    parsed = GAZETTEER.parse(message["hint"], max_words=CONSTITUTION.world.hint_max_words)
    assert parsed == decoy  # the decoy really crossed the wire
    sealed = session.records[-1]
    assert sealed.payload["intent"] == VERDICT_LIE  # the audit sees the honest label


def test_silent_brains_keep_the_truthful_default() -> None:
    session = _thief_session()  # config-selected brain proposes no hint fields
    message = session.take_turn(now=0.0)
    sealed = session.records[-1]
    assert sealed.payload["intent"] == VERDICT_TRUTH
    parsed = GAZETTEER.parse(message["hint"], max_words=CONSTITUTION.world.hint_max_words)
    assert parsed == GAZETTEER.nearest(session.position)


def test_observation_carries_the_deception_construction_kit() -> None:
    session = _thief_session()
    spy = _SpyBrain()
    session.brain = spy
    session.take_turn(now=0.0)
    from copthief_core.domain.state_machine import GameState

    session.machine.state = GameState.COMPUTING_MOVE  # as if the reply arrived
    session.take_turn(now=1.0)
    first, second = spy.seen[0], spy.seen[1]
    assert first.gazetteer is GAZETTEER
    assert first.pheromones is CONSTITUTION.pheromones
    assert first.own_smell == {}  # nothing transmitted before our first turn
    assert second.own_smell  # by turn two, our own trail has crossed the wire


def test_configured_hint_bank_reaches_the_wire() -> None:
    # M5-6: [strategy] hint_bank selects the bank the verbal layer speaks; the
    # winner of the A/B run ships here. Unset ("") keeps the default bank.
    from dataclasses import replace

    from copthief_core.strategy.hints import BANKS

    terse_private = replace(PRIVATE, hint_bank="terse")
    session = PeerSession(CONSTITUTION, terse_private, role="thief", seed=9, gazetteer=GAZETTEER)
    message = session.take_turn(now=0.0)
    landmark = GAZETTEER.parse(message["hint"], max_words=CONSTITUTION.world.hint_max_words)
    assert landmark is not None  # the bank still round-trips on the wire
    rendered = {t.format(landmark=landmark) for t in BANKS["terse"]}
    assert message["hint"] in rendered  # and the wording really is the terse bank's


def test_peer_observation_carries_the_signed_clock() -> None:
    session = _thief_session()
    spy = _SpyBrain()
    session.brain = spy
    session.take_turn(now=0.0)
    movement = CONSTITUTION.movement
    assert spy.seen[0].survival_threshold == movement.survival_threshold
    assert spy.seen[0].max_moves == movement.max_moves


def test_decide_template_preserves_hint_fields_through_the_clamp() -> None:
    board = CONSTITUTION.board.make_board()
    belief = BeliefFilter(
        board=board,
        move_set=CONSTITUTION.movement.move_set,
        start=(0, 0),
        center_intensity=CONSTITUTION.pheromones.center_intensity,
        decay=CONSTITUTION.pheromones.decay,
        smell_trust=PRIVATE.smell_trust_weight,
        hint_trust=PRIVATE.hint_trust_default,
    )
    decoy = GAZETTEER.landmarks()[0]
    decision = _LiarBrain(decoy).decide(
        Observation(
            board=board,
            position=(3, 3),
            move_set=CONSTITUTION.movement.move_set,
            role="thief",
            step=1,
        ),
        belief,
    )
    assert decision.hint_verdict == VERDICT_LIE
    assert decision.hint_landmark == decoy

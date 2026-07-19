"""Referee verbal seam (TODO M5-6; PRD_thief_brain §3 M5-6 seam): hints in referee mode.

With a gazetteer, the referee threads the thief's hint decisions into the police
belief exactly as the peer inbound path does (compose → closed-vocabulary parse →
update_hint, after predict+scent), and records a per-hint efficacy trace against the
GROUND TRUTH it holds: error = 1 − P(true thief cell) (the M3-3 metric identity).
Without a gazetteer nothing changes — the M3/M5 referee pins stay byte-identical.
"""

from pathlib import Path

from copthief_core.domain.belief import BeliefFilter
from copthief_core.shared.config import load_all, load_gazetteer
from copthief_core.strategy.brains import BrainBase, Observation
from copthief_core.strategy.decision import Decision
from copthief_core.strategy.hints import VERDICT_LIE
from copthief_core.strategy.referee import play_referee_game
from copthief_core.strategy.verbal import HintTraceRow

CONSTITUTION, PRIVATE, _LIMITS = load_all(Path("config"), counted=False)
GAZETTEER = load_gazetteer(
    Path("config") / "gazetteer.json",
    map_area=CONSTITUTION.world.map_area,
    board=CONSTITUTION.board.make_board(),
)


class _SitterBrain(BrainBase):
    """Never moves; says nothing (its hints compose as the truthful default)."""

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        return "STAY"


class _SittingLiarBrain(BrainBase):
    """Never moves; lies every turn toward the landmark farthest from itself."""

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        return "STAY"

    def _decide(self, observation: Observation, belief: BeliefFilter) -> Decision:
        decoy = (
            observation.gazetteer.farthest(observation.position) if observation.gazetteer else None
        )
        return Decision(move="STAY", hint_verdict=VERDICT_LIE, hint_landmark=decoy)


def _trace_for(thief_brain: BrainBase) -> list[HintTraceRow]:
    trace: list[HintTraceRow] = []
    play_referee_game(
        CONSTITUTION,
        police_brain=_SitterBrain(seed=1),
        thief_brain=thief_brain,
        smell_trust=PRIVATE.smell_trust_weight,
        seed=5,
        gazetteer=GAZETTEER,
        hint_trust=PRIVATE.hint_trust_default,
        verbal_trace=trace,
    )
    return trace


def test_lying_hints_push_the_police_belief_off_the_truth() -> None:
    trace = _trace_for(_SittingLiarBrain(seed=2))
    assert trace
    assert all(row.verdict == VERDICT_LIE for row in trace)
    deltas = [row.error_after - row.error_before for row in trace]
    assert sum(deltas) / len(deltas) > 0.0  # induced belief error: the lie WORKS


def test_truthful_hints_sharpen_the_police_belief() -> None:
    trace = _trace_for(_SitterBrain(seed=2))
    assert trace
    deltas = [row.error_after - row.error_before for row in trace]
    assert sum(deltas) / len(deltas) <= 0.0  # truth never hurts the tracker


def test_without_a_gazetteer_the_referee_is_unchanged_and_traceless() -> None:
    trace: list[HintTraceRow] = []
    with_verbal = play_referee_game(
        CONSTITUTION,
        police_brain=_SitterBrain(seed=1),
        thief_brain=_SitterBrain(seed=2),
        smell_trust=PRIVATE.smell_trust_weight,
        seed=5,
        verbal_trace=trace,
    )
    assert trace == []  # no gazetteer, no verbal layer, no rows
    bare = play_referee_game(
        CONSTITUTION,
        police_brain=_SitterBrain(seed=1),
        thief_brain=_SitterBrain(seed=2),
        smell_trust=PRIVATE.smell_trust_weight,
        seed=5,
    )
    assert with_verbal == bare

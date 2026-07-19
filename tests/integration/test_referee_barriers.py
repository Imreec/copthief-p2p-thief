"""Referee-mode barrier support (M5-2; PRD_police_brain §4): Decisions end-to-end.

The referee applies police `Decision`s: a barrier joins the ground-truth board AND both
belief filters (motion + occupancy), the cop forgoes its step, and the three capture
forms resolve through the one rules module. A scripted waller proves capture-by-barrier
through the full harness; the seeded ref-police proves quota bookkeeping.
"""

from pathlib import Path

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.rules import Outcome
from copthief_core.shared.config import load_all
from copthief_core.strategy.brains import BrainBase, Observation, make_brain
from copthief_core.strategy.decision import Decision
from copthief_core.strategy.referee import play_referee_game

CONSTITUTION, PRIVATE, _LIMITS = load_all(Path("config"), counted=False)


class _SitterBrain(BrainBase):
    """Never moves — the anvil for the barrier-capture script."""

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        return "STAY"


class _BeliefWallerBrain(BrainBase):
    """Walk to the belief argmax; wall it the moment it is adjacent (capture-by-barrier)."""

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        target = belief.argmax()
        candidates = sorted(
            m
            for m in observation.move_set
            if not observation.board.is_blocked(
                observation.board.apply_move(observation.position, m)
            )
        )
        return min(
            candidates,
            key=lambda m: (
                abs(observation.board.apply_move(observation.position, m)[0] - target[0])
                + abs(observation.board.apply_move(observation.position, m)[1] - target[1])
            ),
        )

    def _decide(self, observation: Observation, belief: BeliefFilter) -> Decision:
        target = belief.argmax()
        if target in observation.board.neighbors(observation.position):
            return Decision(barrier=target)
        return Decision(move=self._pick_move(observation, belief))


def test_scripted_waller_captures_by_barrier_through_the_referee() -> None:
    result = play_referee_game(
        CONSTITUTION,
        police_brain=_BeliefWallerBrain(seed=1),
        thief_brain=_SitterBrain(seed=2),
        smell_trust=PRIVATE.smell_trust_weight,
        seed=1,
    )
    assert result.outcome is Outcome.COP_CAPTURE
    assert result.barriers_placed == 1  # the wall landed on the sitting thief's cell


def test_ref_police_barriers_respect_the_signed_quota_and_stay_reproducible() -> None:
    def run() -> tuple[Outcome, int, int]:
        result = play_referee_game(
            CONSTITUTION,
            police_brain=make_brain(
                "ref-police", seed=11, options={"ref_police_barrier_chance": 1.0}
            ),
            thief_brain=make_brain("random", seed=12),
            smell_trust=PRIVATE.smell_trust_weight,
            seed=6,
        )
        return (result.outcome, result.steps, result.barriers_placed)

    outcome, _steps, placed = run()
    assert run() == (outcome, _steps, placed)
    assert 0 < placed <= CONSTITUTION.movement.max_barriers
    assert outcome in (Outcome.COP_CAPTURE, Outcome.THIEF_SURVIVAL)


class _ClockSpyBrain(BrainBase):
    """Sits still and records every observation (pins the signed-clock fields)."""

    def __init__(self, *, seed: int) -> None:
        super().__init__(seed=seed)
        self.seen: list[Observation] = []

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        self.seen.append(observation)
        return "STAY"


def test_referee_observations_carry_the_signed_clock() -> None:
    police, thief = _ClockSpyBrain(seed=1), _ClockSpyBrain(seed=2)
    play_referee_game(
        CONSTITUTION,
        police_brain=police,
        thief_brain=thief,
        smell_trust=PRIVATE.smell_trust_weight,
        seed=1,
    )
    movement = CONSTITUTION.movement
    assert police.seen
    assert thief.seen
    for seen in (*police.seen, *thief.seen):
        assert seen.survival_threshold == movement.survival_threshold
        assert seen.max_moves == movement.max_moves


def test_start_overrides_relocate_the_game_without_touching_the_constitution() -> None:
    # Adjacent overridden starts + a greedy cop + a sitting thief = capture on step 1 —
    # only possible if the overrides actually moved both agents off the signed starts.
    result = play_referee_game(
        CONSTITUTION,
        police_brain=make_brain("greedy-manhattan", seed=1),
        thief_brain=_SitterBrain(seed=2),
        smell_trust=PRIVATE.smell_trust_weight,
        seed=3,
        cop_start=(5, 6),
        thief_start=(6, 6),
    )
    assert result.outcome is Outcome.COP_CAPTURE
    assert result.steps == 1

"""Confidence-gated flight ramp (M7-47) — ⚑ thief repo only.

The distance term is worth multiplying only when the belief it is computed from is
worth trusting. The clock-anchored ramp fires late in the game whatever we know;
this one fires whenever the belief has collapsed onto a single cell — which on the
live peer path means the cop DECLARED its position (App E rules 21-22 make a false
claim a forfeit, so `note_claim` treats it as certainty).

Kept as a SEPARATE multiplier from `ramp_multiplier` on purpose: the clock ramp is
GA-tuned and its value is evidence, so the new behaviour rides on its own knob and
fires only on a condition that never held before. Against a cop we cannot localise
the gate stays shut and the brain is bit-for-bit the one the GA tuned — which is
what stops this from being the M7-21 mistake a second time.
"""

from copthief_core.domain.board import Board
from copthief_core.strategy.brains import Observation
from copthief_thief.features import resolve_options, survival_ramp

MOVE_SET = ("N", "S", "E", "W", "STAY")
OPTS = resolve_options({})


def observation(step: int, *, survival_threshold: int = 35) -> Observation:
    return Observation(
        board=Board(grid_size=7, axis_origin_corner="top-left", axis_start_index=0),
        position=(3, 3),
        move_set=MOVE_SET,
        role="thief",
        step=step,
        survival_threshold=survival_threshold,
        max_moves=35,
    )


def test_a_smeared_belief_early_does_not_ramp() -> None:
    assert survival_ramp(OPTS, observation(4), 0.2) == 1.0


def test_omitting_confidence_reproduces_the_clock_only_ramp() -> None:
    """Every pre-M7-47 caller must be byte-identical — the GA's evidence stands."""
    assert survival_ramp(OPTS, observation(4)) == 1.0
    assert survival_ramp(OPTS, observation(34)) == OPTS["ramp_multiplier"]


def test_a_collapsed_belief_ramps_whatever_the_clock_says() -> None:
    """A declared cop cell collapses the posterior to 1.0 — that is the trigger."""
    assert survival_ramp(OPTS, observation(4), 1.0) == OPTS["sharp_ramp_multiplier"]


def test_the_gate_is_the_configured_mass() -> None:
    just_under = OPTS["sharp_ramp_mass"] - 0.01
    assert survival_ramp(OPTS, observation(4), just_under) == 1.0
    assert survival_ramp(OPTS, observation(4), OPTS["sharp_ramp_mass"]) > 1.0


def test_late_and_sharp_takes_the_stronger_of_the_two() -> None:
    ramp = survival_ramp(OPTS, observation(34), 1.0)
    assert ramp == max(OPTS["ramp_multiplier"], OPTS["sharp_ramp_multiplier"])


def test_no_clock_still_honours_a_sharp_belief() -> None:
    """An observation without a signed clock (0) has no endgame — but it can still see."""
    assert survival_ramp(OPTS, observation(2, survival_threshold=0), 1.0) > 1.0


def test_the_sharp_gate_can_be_configured_shut() -> None:
    opts = resolve_options({"sharp_ramp_mass": 2.0})  # unreachable: mass is a probability
    assert survival_ramp(opts, observation(4), 1.0) == 1.0


def test_step_one_certainty_is_common_knowledge_not_a_read() -> None:
    """The filter opens as a delta on the SIGNED start — both sides already know it."""
    assert survival_ramp(OPTS, observation(1), 1.0) == 1.0
    assert survival_ramp(OPTS, observation(2), 1.0) == OPTS["sharp_ramp_multiplier"]

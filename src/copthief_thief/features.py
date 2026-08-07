"""ThiefBrain option defaults + move scoring (PRD_thief_brain §3).

`DEFAULT_OPTIONS` is a data table, not logic (AppFTable pattern): canonical knob
values, overridden by `[strategy.thief]` / arena `brain_options` — the M5-4 GA
interface. Scoring is one-ply with an adversarial threat model: the plies are spent
on AREA analysis (two-front region, articulation traps), not tree depth.

Time-shaped knobs anchor to the SIGNED clock the core Observation carries since
cop #36 (`survival_threshold`): `ramp_start_fraction` scales the threshold and the
trap ceiling scales the REMAINING steps — the knobs stay GA-tunable fractions, the
anchors stop being private copies of signed terms (PRD_thief_brain §3 deviation
retired). An observation without a clock (0) means no endgame and a cap-sized
trap horizon.
"""

from __future__ import annotations

from collections.abc import Mapping

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import Coord
from copthief_core.strategy.brains import Observation

DEFAULT_OPTIONS: dict[str, float] = {
    "top_k": 4.0,  # cop-belief truncation - sharper flight vector beat 6 on DoD+holdout
    "siege_top_k": 1.0,  # truncation once the cop walls every turn (M7-46)
    "siege_min_walls": 2.0,  # walls before a rate means anything (one early wall is noise)
    "siege_wall_rate": 0.5,  # walls per elapsed step at/above which it IS a siege
    "w_distance": 3.0,  # per-cell worst-case-distance reward
    "w_region": 1.0,  # per-cell two-front safe-region reward
    "w_articulation": 20.0,  # flat penalty for entering a cheaply-sealable pocket
    "trap_size_fraction": 0.3,  # trap ceiling = this fraction of the capped remaining clock
    "w_spread": 0.5,  # unvisited-cell bonus (the reference thief's good instinct)
    "ramp_start_fraction": 0.7,  # survival clock: ramp from this fraction of the threshold
    "ramp_multiplier": 3.0,  # distance-weight multiplier once the ramp is on
    "sharp_ramp_mass": 0.9,  # belief peak mass at which we KNOW, not guess (M7-47)
    "sharp_ramp_multiplier": 3.0,  # distance multiplier while the cop's cell is known
    "sharp_ramp_min_step": 2.0,  # skip step 1: the signed start is common knowledge
    "region_cap": 30.0,  # BFS early-exit for region counts
    "mirror_smell_trust": 4.0,  # the mirror's assumed opponent scent trust
    "mirror_sharp_p": 0.35,  # exposure at/above which they "know where we are"
    "near_distance": 4.0,  # argmax distance at/below which they "can act on it"
    "lie_budget": 3.0,  # lies per mini-game (credibility is a budget)
    "lie_cooldown": 4.0,  # steps between lies
    "decision_budget_seconds": 5.0,  # generous per-decision ceiling (perf pin)
}


def resolve_options(options: Mapping[str, float]) -> dict[str, float]:
    """The defaults table with config overrides applied (unknown keys tolerated)."""
    return {**DEFAULT_OPTIONS, **options}


def under_siege(opts: Mapping[str, float], observation: Observation) -> bool:
    """True once the opponent's wall RATE marks it a sieging pursuer (M7-46).

    Read off OUR OWN board — every barrier is declared and sealed, so the count is
    certain, unlike anything scent-derived. A thief's `barriers_used` is always 0, so
    the signal has to be `board.barriers`. The absolute floor gates the rate: one wall
    on step 2 is a rate of 1.0 and means nothing.
    """
    walls = len(observation.board.barriers)
    if walls < opts["siege_min_walls"]:
        return False
    return walls / max(observation.step - 1, 1) >= opts["siege_wall_rate"]


def support_width(opts: Mapping[str, float], observation: Observation) -> int:
    """How many belief cells the flight vector averages over this turn.

    The `top_k` hedge buys robustness against a pursuer we localise loosely, and costs
    us against one that walls every turn — a siege closes the gap faster than a smeared
    support lets us flee (the 2026-08-07 uoh-sqak friendly, all three thief sub-games).
    Off siege this returns `top_k` unchanged, so a cop that rarely walls sees exactly
    the brain the GA tuned.
    """
    return int(opts["siege_top_k"] if under_siege(opts, observation) else opts["top_k"])


def survival_ramp(
    opts: Mapping[str, float], observation: Observation, confidence: float = 0.0
) -> float:
    """The distance-weight multiplier, from two independent triggers (M7-47).

    CLOCK — ramps once `step ≥ ramp_start_fraction × threshold`, anchored to the SIGNED
    survival threshold; no clock (0) = no endgame. GA-tuned, left exactly as it was.

    BELIEF — `confidence` is the mass on the belief's peak. A posterior collapsed onto
    one cell means the cop DECLARED its position (a false claim forfeits under App E
    rules 21-22, so `note_claim` treats it as certainty), and a distance term computed
    from a cell we KNOW is worth multiplying whatever the clock says. Against a cop we
    can only guess at, the gate stays shut and this returns the pre-M7-47 value — which
    is the point: fleeing hard from a smeared belief is worse than not fleeing hard,
    measured, and a single unconditional ramp collapsed us 8/8 → 0/8 against a quiet
    chaser (`docs/evidence/m7-47-informed-ramp.md`).

    Step 1 is excluded (`sharp_ramp_min_step`): the filter opens as a delta on the
    SIGNED start, which is common knowledge on both sides rather than anything we read
    off this opponent, and treating it as a read cost a DoD game.
    """
    threshold = observation.survival_threshold
    late = threshold > 0 and observation.step >= opts["ramp_start_fraction"] * threshold
    ramp = opts["ramp_multiplier"] if late else 1.0
    if observation.step >= opts["sharp_ramp_min_step"] and confidence >= opts["sharp_ramp_mass"]:
        return max(ramp, opts["sharp_ramp_multiplier"])
    return ramp


def trap_ceiling(opts: Mapping[str, float], observation: Observation) -> float:
    """Sealed-component size below which a pocket is a trap: a tunable fraction of
    the steps still to survive (capped by `region_cap`; no clock = the cap itself) —
    a pocket that outlasts the clock is safe ground, not a trap."""
    cap = opts["region_cap"]
    threshold = observation.survival_threshold
    horizon = min(max(threshold - observation.step, 0), cap) if threshold > 0 else cap
    return opts["trap_size_fraction"] * horizon


def truncated_support(belief: BeliefFilter, top_k: int) -> list[tuple[Coord, float]]:
    """The `top_k` most probable cop cells, renormalized (deterministic order)."""
    ranked = sorted(belief.probs().items(), key=lambda kv: (-kv[1], kv[0]))[:top_k]
    total = sum(p for _, p in ranked)
    return [(cell, p / total) for cell, p in ranked] if total > 0 else []


def worst_case_distance(dest: Coord, support: list[tuple[Coord, float]]) -> float:
    """Expected distance to the believed cop AFTER its best reply (one step closes 1)."""
    return sum(
        p * max(abs(dest[0] - cell[0]) + abs(dest[1] - cell[1]) - 1, 0) for cell, p in support
    )

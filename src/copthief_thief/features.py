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
    "w_distance": 3.0,  # per-cell worst-case-distance reward
    "w_region": 1.0,  # per-cell two-front safe-region reward
    "w_articulation": 20.0,  # flat penalty for entering a cheaply-sealable pocket
    "trap_size_fraction": 0.3,  # trap ceiling = this fraction of the capped remaining clock
    "w_spread": 0.5,  # unvisited-cell bonus (the reference thief's good instinct)
    "ramp_start_fraction": 0.7,  # survival clock: ramp from this fraction of the threshold
    "ramp_multiplier": 3.0,  # distance-weight multiplier once the ramp is on
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


def survival_ramp(opts: Mapping[str, float], observation: Observation) -> float:
    """The distance-weight multiplier, anchored to the SIGNED survival threshold:
    ramps once `step ≥ ramp_start_fraction × threshold`; no clock (0) = no endgame."""
    threshold = observation.survival_threshold
    if threshold <= 0 or observation.step < opts["ramp_start_fraction"] * threshold:
        return 1.0
    return opts["ramp_multiplier"]


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

"""ThiefBrain option defaults + move scoring (PRD_thief_brain §3).

`DEFAULT_OPTIONS` is a data table, not logic (AppFTable pattern): canonical knob
values, overridden by `[strategy.thief]` / arena `brain_options` — the M5-4 GA
interface. Scoring is one-ply with an adversarial threat model: the plies are spent
on AREA analysis (two-front region, articulation traps), not tree depth.

Documented deviation from PRD_thief_brain §3: the Observation carries no
`survival_threshold`, so the survival clock and trap sizing ride private knobs
(`ramp_start_step`, `trap_region_min`) instead of the signed values — strategy
tunables, not copies of signed terms (noted for a future core Observation field).
"""

from __future__ import annotations

from collections.abc import Mapping

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import Coord

DEFAULT_OPTIONS: dict[str, float] = {
    "top_k": 4.0,  # cop-belief truncation - sharper flight vector beat 6 on DoD+holdout
    "w_distance": 3.0,  # per-cell worst-case-distance reward
    "w_region": 1.0,  # per-cell two-front safe-region reward
    "w_articulation": 20.0,  # flat penalty for entering a cheaply-sealable pocket
    "trap_region_min": 9.0,  # sealed-component size below which a pocket is a trap
    "w_spread": 0.5,  # unvisited-cell bonus (the reference thief's good instinct)
    "ramp_start_step": 25.0,  # survival clock: from here distance dominates
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

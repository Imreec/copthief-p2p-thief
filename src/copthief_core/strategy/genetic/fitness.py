"""GA fitness evaluation, split from `genetic/runs` at M7-20 (150-line rule).

The claim-policy door (evolve under the threshold we actually play) pushed the module
past the limit, so the CONFIG concern stays in `runs` and the SCORING concern lives
here. Split, never compressed — the two were always separable: one parses a file, the
other plays games.
"""

from __future__ import annotations

from typing import Any

from copthief_core.domain.rules import Outcome
from copthief_core.shared.config_model import Constitution
from copthief_core.shared.locked_models import LockedModelRegistry
from copthief_core.strategy.genetic.runs import GaConfig
from copthief_core.strategy.scenarios import Scenario, play_scenario_series

__all__ = ["fitness", "opponent_fitness"]


def opponent_fitness(
    config: GaConfig,
    constitution: Constitution,
    smell_trust: float,
    scenarios: list[Scenario],
    candidate_options: dict[str, float],
    opponent: dict[str, Any],
    locked_models: LockedModelRegistry | None,
) -> float:
    """Win-rate of the candidate vs ONE opponent ({spec, feed?, claim_feed?, options?}).

    M7-20: the series runs under `config.claim_threshold`, so a candidate is scored on
    the captures it can actually convert — a claim it never makes forfeits the landing.
    """
    spec = str(opponent["spec"])
    feed = opponent.get("feed")
    options = {str(k): float(v) for k, v in opponent.get("options", {}).items()}
    police = config.brain if config.role == "police" else spec
    thief = spec if config.role == "police" else config.brain
    police_options = candidate_options if config.role == "police" else options
    thief_options = options if config.role == "police" else candidate_options
    results = play_scenario_series(
        constitution,
        police_brain_name=police,
        thief_brain_name=thief,
        smell_trust=smell_trust,
        scenarios=scenarios,
        police_options=police_options,
        thief_options=thief_options,
        thief_feed_name=feed if config.role == "police" else config.candidate_feed,
        police_feed_name=feed if config.role == "thief" else config.candidate_feed,
        scent_model_name=config.scent_model,
        locked_models=locked_models,
        claim_threshold=config.claim_threshold,
        thief_claim_feed_name=config.claim_feed_for(opponent),
    )
    winning = Outcome.COP_CAPTURE if config.role == "police" else Outcome.THIEF_SURVIVAL
    return sum(r.outcome is winning for r in results) / len(results)


def fitness(
    config: GaConfig,
    constitution: Constitution,
    smell_trust: float,
    scenarios: list[Scenario],
    candidate_options: dict[str, float],
    *,
    locked_models: LockedModelRegistry | None = None,
) -> float:
    """The candidate's mean win-rate for `config.role` across the opponent pool.

    M7-14: `config.scent_model` (resolved against `locked_models`) selects the
    physics the whole run is tuned under; an opponent's `feed` lands on whichever
    side that opponent plays. M7-15: with `opponent_pool` set, fitness is the plain
    mean over its members; empty = the single configured opponent, unchanged.
    """
    pool = config.opponent_pool or (
        {"spec": config.opponent, "feed": config.opponent_feed, "options": config.opponent_options},
    )
    scores = [
        opponent_fitness(
            config, constitution, smell_trust, scenarios, candidate_options, member, locked_models
        )
        for member in pool
    ]
    return sum(scores) / len(scores)

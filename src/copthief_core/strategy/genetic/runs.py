"""GA config loading + fitness (M5-4): config-driven, role-blind, referee-mode only.

Fitness = the candidate brain's win-rate for the configured role against the fixed
reference opponent over a fresh scenario-seed suite (never the DoD seeds — the gate
is not a training target). The mirrored copy of this module evolves whatever brain
the LOCAL `config/ga.json` names (PR #29 rule).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from copthief_core.domain.rules import Outcome
from copthief_core.shared.config_model import Constitution
from copthief_core.shared.locked_models import LockedModelRegistry
from copthief_core.shared.private_config import ConfigError, validated_version
from copthief_core.strategy.genetic.genome import GeneSpec
from copthief_core.strategy.scenarios import Scenario, play_scenario_series


@dataclass(frozen=True)
class GaPhase:
    """One evolution schedule (the committed run, or the CI smoke)."""

    seed: int
    population: int
    generations: int
    elite_count: int
    tournament_size: int
    crossover_blend: float
    mutation_sigma: float
    mutation_rate: float
    fitness_seeds: tuple[int, ...]
    scenario_min_separation: int


@dataclass(frozen=True)
class GaConfig:
    """The typed `config/ga.json`."""

    version: str
    role: str
    brain: str
    opponent: str
    opponent_options: dict[str, float]
    genes: dict[str, tuple[float, float]]
    run: GaPhase
    smoke: GaPhase
    artifact_out: str
    evidence_out: str
    # M7-14 doors, both defaulting to the shipped behavior: the run's named physics
    # and the fixed opponent's information feed (strategy/info_feed.make_feed names).
    scent_model: str | None = None
    opponent_feed: str | None = None
    # M7-15: an OPPONENT POOL — fitness is the plain mean across members (each a
    # {spec, feed?, options?} dict). A GA tuned against one opponent overfits to it
    # (the book-v1 single-opponent retune beat the claim-reader and stalled against
    # a random walker); empty = the single `opponent` above, unchanged.
    opponent_pool: tuple[dict[str, Any], ...] = ()

    def spec(self) -> GeneSpec:
        """The search box in fixed (sorted) gene order."""
        names = tuple(sorted(self.genes))
        return GeneSpec(
            names=names,
            low=tuple(self.genes[n][0] for n in names),
            high=tuple(self.genes[n][1] for n in names),
        )


def _phase(raw: dict[str, Any]) -> GaPhase:
    return GaPhase(
        seed=int(raw["seed"]),
        population=int(raw["population"]),
        generations=int(raw["generations"]),
        elite_count=int(raw["elite_count"]),
        tournament_size=int(raw["tournament_size"]),
        crossover_blend=float(raw["crossover_blend"]),
        mutation_sigma=float(raw["mutation_sigma"]),
        mutation_rate=float(raw["mutation_rate"]),
        fitness_seeds=tuple(int(s) for s in raw["fitness_seeds"]),
        scenario_min_separation=int(raw["scenario_min_separation"]),
    )


def load_ga_config(path: Path) -> GaConfig:
    """Load + validate (Raises: ConfigError on bad shape — same posture as arena.json)."""
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    try:
        return GaConfig(
            version=validated_version(raw, path.name),
            role=str(raw["role"]),
            brain=str(raw["brain"]),
            opponent=str(raw["opponent"]),
            opponent_options={str(k): float(v) for k, v in raw.get("opponent_options", {}).items()},
            genes={str(name): (float(box[0]), float(box[1])) for name, box in raw["genes"].items()},
            run=_phase(raw["run"]),
            smoke=_phase(raw["smoke"]),
            artifact_out=str(raw["artifact_out"]),
            evidence_out=str(raw["evidence_out"]),
            scent_model=(None if raw.get("scent_model") is None else str(raw["scent_model"])),
            opponent_feed=(None if raw.get("opponent_feed") is None else str(raw["opponent_feed"])),
            opponent_pool=tuple(dict(member) for member in raw.get("opponent_pool", [])),
        )
    except (KeyError, TypeError, ValueError, IndexError) as error:
        raise ConfigError(f"{path.name}: malformed GA config — {error}") from error


def _fitness_vs(
    config: GaConfig,
    constitution: Constitution,
    smell_trust: float,
    scenarios: list[Scenario],
    candidate_options: dict[str, float],
    opponent: dict[str, Any],
    locked_models: LockedModelRegistry | None,
) -> float:
    """Win-rate of the candidate vs ONE opponent ({spec, feed?, options?})."""
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
        thief_feed_name=feed if config.role == "police" else None,
        police_feed_name=feed if config.role == "thief" else None,
        scent_model_name=config.scent_model,
        locked_models=locked_models,
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
        _fitness_vs(
            config, constitution, smell_trust, scenarios, candidate_options, member, locked_models
        )
        for member in pool
    ]
    return sum(scores) / len(scores)

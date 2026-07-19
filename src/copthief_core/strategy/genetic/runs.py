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
        )
    except (KeyError, TypeError, ValueError, IndexError) as error:
        raise ConfigError(f"{path.name}: malformed GA config — {error}") from error


def fitness(
    config: GaConfig,
    constitution: Constitution,
    smell_trust: float,
    scenarios: list[Scenario],
    candidate_options: dict[str, float],
) -> float:
    """The candidate's win-rate for `config.role` vs the fixed opponent."""
    police = config.brain if config.role == "police" else config.opponent
    thief = config.opponent if config.role == "police" else config.brain
    police_options = candidate_options if config.role == "police" else config.opponent_options
    thief_options = config.opponent_options if config.role == "police" else candidate_options
    results = play_scenario_series(
        constitution,
        police_brain_name=police,
        thief_brain_name=thief,
        smell_trust=smell_trust,
        scenarios=scenarios,
        police_options=police_options,
        thief_options=thief_options,
    )
    winning = Outcome.COP_CAPTURE if config.role == "police" else Outcome.THIEF_SURVIVAL
    return sum(r.outcome is winning for r in results) / len(results)

"""Seeded generational GA loop (M5-4; HW6 salvage adapted): elitist, reproducible.

One `random.Random(phase.seed)` threads the initial population and every operator —
a fixed seed reproduces the run byte-for-byte. Elitism carries the top individuals
unchanged, so best fitness is non-decreasing: the property the CI smoke asserts and
the committed fitness curve's headline.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

from copthief_core.shared.config import load_all
from copthief_core.strategy.genetic.genome import decode, random_genome
from copthief_core.strategy.genetic.operators import (
    blend_crossover,
    gaussian_mutate,
    tournament_select,
)
from copthief_core.strategy.genetic.runs import GaConfig, GaPhase, fitness
from copthief_core.strategy.scenarios import scenario_suite


@dataclass(frozen=True)
class Generation:
    """One generation's fitness summary — the points the committed curve plots."""

    best: float
    mean: float


@dataclass(frozen=True)
class EvolutionResult:
    """The evolved outcome: options, fitness, and the per-generation history."""

    best_options: dict[str, float]
    best_fitness: float
    default_fitness: float
    history: tuple[Generation, ...]


def evolve(config: GaConfig, phase: GaPhase, config_dir: Path | None = None) -> EvolutionResult:
    """Run one elitist evolution under `phase` (Input: GA config + schedule + config
    tree; Output: best individual + curve; deterministic per seed)."""
    constitution, private, _ = load_all(config_dir or Path("config"), counted=False)
    scenarios = list(
        scenario_suite(
            constitution,
            seeds=phase.fitness_seeds,
            min_separation=phase.scenario_min_separation,
        )
    )
    spec = config.spec()
    rng = random.Random(phase.seed)

    def score(genome: list[float]) -> float:
        return fitness(
            config,
            constitution,
            private.smell_trust_weight,
            scenarios,
            decode(spec, genome),
            locked_models=private.locked_models,
        )

    default_fitness = fitness(
        config,
        constitution,
        private.smell_trust_weight,
        scenarios,
        {},
        locked_models=private.locked_models,
    )
    population = [random_genome(spec, rng) for _ in range(phase.population)]
    scored = sorted(((genome, score(genome)) for genome in population), key=lambda pair: -pair[1])
    history: list[Generation] = []
    for _ in range(phase.generations):
        history.append(
            Generation(
                best=scored[0][1],
                mean=sum(fit for _, fit in scored) / len(scored),
            )
        )
        elites = [genome[:] for genome, _ in scored[: phase.elite_count]]
        children = elites[:]
        while len(children) < phase.population:
            mother = tournament_select(scored, phase.tournament_size, rng)
            father = tournament_select(scored, phase.tournament_size, rng)
            child = blend_crossover(spec, mother, father, phase.crossover_blend, rng)
            child = gaussian_mutate(spec, child, phase.mutation_sigma, phase.mutation_rate, rng)
            children.append(child)
        rescored = [(genome, score(genome)) for genome in children[phase.elite_count :]]
        scored = sorted(
            [*((elite, scored[i][1]) for i, elite in enumerate(elites)), *rescored],
            key=lambda pair: -pair[1],
        )
    best_genome, best_fitness = scored[0]
    return EvolutionResult(
        best_options=decode(spec, best_genome),
        best_fitness=best_fitness,
        default_fitness=default_fitness,
        history=tuple(history),
    )

"""Seeded start scenarios + scenario series (M5-2; PRD_police_brain §4).

Deterministic brains on the fixed signed starts collapse a series to one repeated game;
a win-RATE needs varied, reproducible boards. Scenario #1 is always the constitution's
canonical start pair; every other seed samples a legal pair under the config-owned
minimum Manhattan separation. Referee-mode evaluation only — live games always play the
signed starts (the suite is an instrument, not a rule change). HW6 GA fitness-suite
precedent, adapted (ADR-0002-logged salvage).
"""

from __future__ import annotations

import random
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from copthief_core.domain.board import Coord
from copthief_core.shared.config_model import Constitution
from copthief_core.shared.locked_models import LockedModelRegistry, build_scent_model
from copthief_core.strategy.brains import make_brain
from copthief_core.strategy.info_feed import BeliefFeed, make_feed
from copthief_core.strategy.referee import RefereeGameResult, play_referee_game


@dataclass(frozen=True)
class Scenario:
    """One reproducible start pair (the seed also feeds the brains' RNG streams)."""

    seed: int
    cop_start: Coord
    thief_start: Coord


def _sample_pair(
    constitution: Constitution, rng: random.Random, min_separation: int
) -> tuple[Coord, Coord]:
    """A legal (cop, thief) start pair at ≥ `min_separation` Manhattan distance."""
    origin = constitution.board.axis_start_index
    span = range(origin, origin + constitution.board.grid_size)
    cells = [(r, c) for r in span for c in span]
    while True:
        cop, thief = rng.choice(cells), rng.choice(cells)
        if abs(cop[0] - thief[0]) + abs(cop[1] - thief[1]) >= max(min_separation, 1):
            return cop, thief


def scenario_suite(
    constitution: Constitution, *, seeds: Iterable[int], min_separation: int
) -> tuple[Scenario, ...]:
    """One scenario per seed; the first is always the canonical signed start pair."""
    suite: list[Scenario] = []
    for index, seed in enumerate(seeds):
        if index == 0:
            cop, thief = constitution.board.cop_start, constitution.board.thief_start
        else:
            cop, thief = _sample_pair(constitution, random.Random(seed), min_separation)
        suite.append(Scenario(seed=seed, cop_start=cop, thief_start=thief))
    return tuple(suite)


def play_referee_series(
    constitution: Constitution,
    *,
    police_brain_name: str,
    thief_brain_name: str,
    smell_trust: float,
    seeds: Iterable[int],
) -> list[RefereeGameResult]:
    """A headless seeded series on the canonical signed starts (moved from
    strategy/referee at M5-6, 150-line rule): fresh brains per game, two RNG
    streams per seed (police 2n, thief 2n+1) so pairings never share a stream."""
    return [
        play_referee_game(
            constitution,
            police_brain=make_brain(police_brain_name, seed=2 * seed),
            thief_brain=make_brain(thief_brain_name, seed=2 * seed + 1),
            smell_trust=smell_trust,
            seed=seed,
        )
        for seed in seeds
    ]


def play_scenario_series(
    constitution: Constitution,
    *,
    police_brain_name: str,
    thief_brain_name: str,
    smell_trust: float,
    scenarios: Iterable[Scenario],
    police_options: Mapping[str, float] | None = None,
    thief_options: Mapping[str, float] | None = None,
    belief_feed: BeliefFeed | None = None,
    thief_feed_name: str | None = None,
    police_feed_name: str | None = None,
    scent_model_name: str | None = None,
    locked_models: LockedModelRegistry | None = None,
) -> list[RefereeGameResult]:
    """A seeded series over scenarios: fresh brains per game, two RNG streams per seed
    (police 2n, thief 2n+1) so pairings never share a stream.

    M7-14 doors: `scent_model_name` (+ the committed registry) selects the physics for
    every game; `thief_feed_name` / `police_feed_name` name one side's information
    structure, built FRESH PER GAME because a lagged feed carries trajectory history.
    A named police feed pins the thief side to hidden unless the thief names its own —
    the referee's fallback (thief inherits the police feed) is for the symmetric
    balance-study shape, not for named per-side runs. All default to shipped behavior.
    """
    model = None
    if scent_model_name is not None:
        if locked_models is None:
            raise ValueError("scent_model_name requires the locked-model registry")
        model = build_scent_model(locked_models, scent_model_name, constitution.pheromones)

    def side_feed(name: str | None) -> BeliefFeed | None:
        return None if name is None else make_feed(name, constitution, smell_trust=smell_trust)

    def thief_side_feed() -> BeliefFeed | None:
        named = side_feed(thief_feed_name)
        if named is None and police_feed_name is not None:
            return make_feed("hidden", constitution, smell_trust=smell_trust)
        return named

    return [
        play_referee_game(
            constitution,
            police_brain=make_brain(
                police_brain_name, seed=2 * scenario.seed, options=police_options
            ),
            thief_brain=make_brain(
                thief_brain_name, seed=2 * scenario.seed + 1, options=thief_options
            ),
            smell_trust=smell_trust,
            seed=scenario.seed,
            cop_start=scenario.cop_start,
            thief_start=scenario.thief_start,
            belief_feed=side_feed(police_feed_name) or belief_feed,
            thief_belief_feed=thief_side_feed(),
            scent_model=model,
        )
        for scenario in scenarios
    ]

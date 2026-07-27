"""Genetic tuning core (TODO M5-4; PLAN §8 "tuned offline by genetic self-play").

HW6 salvage adapted (ADR-0002-logged): a bounded real-valued genome over a brain's
option keys, seeded generational loop with elitism (best fitness never decreases —
the property the CI smoke asserts and the committed curve's headline), stdlib-only
operators. Config-driven end to end (`config/ga.json`); role-blind (PR #29 rule):
the mirrored copy evolves whatever brain the local config names.
"""

from pathlib import Path

import pytest

from copthief_core.strategy.genetic.evolve import evolve
from copthief_core.strategy.genetic.genome import GeneSpec, clip, decode, random_genome
from copthief_core.strategy.genetic.runs import load_ga_config

CONFIG = load_ga_config(Path("config") / "ga.json")


def test_shipped_ga_config_loads_and_names_this_repos_role_brain() -> None:
    assert CONFIG.role in ("police", "thief")
    assert ":" in CONFIG.brain or CONFIG.brain  # dotted role spec or core name
    assert CONFIG.genes  # non-empty search box
    assert CONFIG.smoke.generations >= 2  # the CI smoke needs a curve to check


def test_genome_stays_inside_the_search_box() -> None:
    spec = GeneSpec(names=("a", "b"), low=(0.0, -1.0), high=(1.0, 1.0))
    assert clip(spec, [5.0, -7.0]) == [1.0, -1.0]
    import random

    genome = random_genome(spec, random.Random(3))
    assert all(lo <= v <= hi for v, lo, hi in zip(genome, spec.low, spec.high, strict=True))
    assert decode(spec, genome) == {"a": genome[0], "b": genome[1]}


def test_smoke_evolution_is_deterministic_with_non_decreasing_best() -> None:
    first = evolve(CONFIG, CONFIG.smoke)
    again = evolve(CONFIG, CONFIG.smoke)
    assert first == again  # one seed, one result — byte-reproducible
    best_curve = [generation.best for generation in first.history]
    assert best_curve == sorted(best_curve)  # elitism: best fitness never decreases
    assert len(best_curve) == CONFIG.smoke.generations
    assert set(first.best_options) == set(CONFIG.genes)
    assert 0.0 <= first.best_fitness <= 1.0


def test_malformed_ga_config_is_refused_loudly(tmp_path: Path) -> None:
    import json

    raw = json.loads((Path("config") / "ga.json").read_text(encoding="utf-8"))
    raw["version"] = "nope"
    path = tmp_path / "ga.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    from copthief_core.shared.private_config import ConfigError

    with pytest.raises(ConfigError):
        load_ga_config(path)


def test_ga_config_parses_the_bookv1_doors_with_safe_defaults() -> None:
    """M7-14: a GA config may name the run's scent model and the opponent's feed;
    both default off so the shipped ga.json is untouched by the feature."""
    import json

    raw = json.loads((Path("config") / "ga.json").read_text(encoding="utf-8"))
    raw["scent_model"] = "multiplicative_book_v1"
    raw["opponent_feed"] = "truth-lag1"
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "ga.json"
        path.write_text(json.dumps(raw), encoding="utf-8")
        config = load_ga_config(path)
    assert config.scent_model == "multiplicative_book_v1"
    assert config.opponent_feed == "truth-lag1"
    assert CONFIG.scent_model is None
    assert CONFIG.opponent_feed is None


def test_fitness_threads_the_doors_to_the_series() -> None:
    """Wiring proof without flaky value asserts: a bogus feed name must surface from
    make_feed, and a named model without the registry must refuse — both can only
    happen if fitness actually passes the doors down."""
    from dataclasses import replace

    from copthief_core.shared.config import load_all
    from copthief_core.strategy.genetic.fitness import fitness
    from copthief_core.strategy.scenarios import scenario_suite

    constitution, private, _ = load_all(Path("config"), counted=False)
    scenarios = list(scenario_suite(constitution, seeds=(301,), min_separation=4))
    bad_feed = replace(CONFIG, opponent_feed="psychic")
    with pytest.raises(ValueError, match="unknown feed"):
        fitness(bad_feed, constitution, private.smell_trust_weight, scenarios, {})
    named_model = replace(CONFIG, scent_model="multiplicative_book_v1")
    with pytest.raises(ValueError, match="registry"):
        fitness(named_model, constitution, private.smell_trust_weight, scenarios, {})
    value = fitness(
        named_model,
        constitution,
        private.smell_trust_weight,
        scenarios,
        {},
        locked_models=private.locked_models,
    )
    assert 0.0 <= value <= 1.0


def test_an_opponent_pool_averages_fitness_across_its_members() -> None:
    """M7-15: a GA tuned against ONE opponent overfits (the book-v1 retune beat the
    claim-reader but stalled vs a random walker). A pool scores the candidate
    against every member over the same scenarios; the fitness is the plain mean —
    pinned exactly against the single-opponent runs it is built from."""
    from dataclasses import replace

    from copthief_core.shared.config import load_all
    from copthief_core.strategy.genetic.fitness import fitness
    from copthief_core.strategy.scenarios import scenario_suite

    constitution, private, _ = load_all(Path("config"), counted=False)
    scenarios = list(scenario_suite(constitution, seeds=(301, 302), min_separation=4))

    def run(config: object) -> float:
        return fitness(
            config,  # type: ignore[arg-type]
            constitution,
            private.smell_trust_weight,
            scenarios,
            {},
            locked_models=private.locked_models,
        )

    lone_a = run(replace(CONFIG, opponent="ref-thief", opponent_feed=None))
    lone_b = run(replace(CONFIG, opponent="belief-evader", opponent_feed="truth-lag1"))
    pooled = run(
        replace(
            CONFIG,
            opponent_pool=(
                {"spec": "ref-thief"},
                {"spec": "belief-evader", "feed": "truth-lag1"},
            ),
        )
    )
    assert pooled == (lone_a + lone_b) / 2


def test_the_pool_parses_from_config_with_safe_defaults() -> None:
    import json
    import tempfile

    raw = json.loads((Path("config") / "ga.json").read_text(encoding="utf-8"))
    raw["opponent_pool"] = [
        {"spec": "ref-thief"},
        {"spec": "belief-evader", "feed": "truth-lag1", "options": {"stay_penalty": 0.0}},
    ]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "ga.json"
        path.write_text(json.dumps(raw), encoding="utf-8")
        config = load_ga_config(path)
    assert len(config.opponent_pool) == 2
    assert config.opponent_pool[0]["spec"] == "ref-thief"
    assert config.opponent_pool[1]["feed"] == "truth-lag1"
    assert CONFIG.opponent_pool == ()

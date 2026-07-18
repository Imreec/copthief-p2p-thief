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

"""Scenario suite (M5-2; PRD_police_brain §4): seeded start pairs for meaningful rates.

Deterministic brains on the fixed signed starts degenerate a series to one repeated
game — the DoD win-rate needs varied, reproducible scenarios. Scenario #1 is always the
constitution's canonical starts; the rest are seeded samples with a config-owned
minimum Manhattan separation. Referee-mode only — live games play the signed starts.
"""

from pathlib import Path

from copthief_core.shared.config import load_all
from copthief_core.strategy.scenarios import Scenario, scenario_suite

CONSTITUTION, _PRIVATE, _LIMITS = load_all(Path("config"), counted=False)
SEEDS = tuple(range(1, 13))


def suite() -> tuple[Scenario, ...]:
    return scenario_suite(CONSTITUTION, seeds=SEEDS, min_separation=4)


def test_first_scenario_is_the_canonical_signed_start_pair() -> None:
    first = suite()[0]
    assert first.cop_start == CONSTITUTION.board.cop_start
    assert first.thief_start == CONSTITUTION.board.thief_start


def test_suite_is_reproducible_and_one_scenario_per_seed() -> None:
    assert suite() == suite()
    assert [s.seed for s in suite()] == list(SEEDS)


def test_sampled_starts_are_in_bounds_distinct_and_separated() -> None:
    board = CONSTITUTION.board.make_board()
    for scenario in suite():
        assert board.in_bounds(scenario.cop_start)
        assert board.in_bounds(scenario.thief_start)
        assert scenario.cop_start != scenario.thief_start
        separation = abs(scenario.cop_start[0] - scenario.thief_start[0]) + abs(
            scenario.cop_start[1] - scenario.thief_start[1]
        )
        assert separation >= 4


def test_sampling_actually_varies_the_starts_across_seeds() -> None:
    pairs = {(s.cop_start, s.thief_start) for s in suite()}
    assert len(pairs) > 1  # not the canonical pair repeated

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


def test_a_lagged_feed_is_fresh_per_game_in_a_scenario_series() -> None:
    """A truth-lag feed carries history; the series must build one PER GAME, or game
    N's opening belief starts on game N-1's trajectory (M7-14). Pinned by the only
    observable that matters: a scenario's result is identical whether it plays alone
    or after another scenario."""
    from copthief_core.strategy.scenarios import play_scenario_series

    both = play_scenario_series(
        CONSTITUTION,
        police_brain_name="greedy-manhattan",
        thief_brain_name="belief-evader",
        smell_trust=_PRIVATE.smell_trust_weight,
        scenarios=suite()[:2],
        thief_feed_name="truth-lag1",
    )
    alone = play_scenario_series(
        CONSTITUTION,
        police_brain_name="greedy-manhattan",
        thief_brain_name="belief-evader",
        smell_trust=_PRIVATE.smell_trust_weight,
        scenarios=suite()[1:2],
        thief_feed_name="truth-lag1",
    )
    assert both[1] == alone[0]


def test_a_scent_model_name_reaches_the_series_games() -> None:
    """The series resolves the model name once against the registry and threads the
    same physics into every game (determinism must survive the door)."""
    from copthief_core.strategy.scenarios import play_scenario_series

    def series() -> list[object]:
        return list(
            play_scenario_series(
                CONSTITUTION,
                police_brain_name="greedy-manhattan",
                thief_brain_name="ref-thief",
                smell_trust=_PRIVATE.smell_trust_weight,
                scenarios=suite()[:4],
                scent_model_name="multiplicative_book_v1",
                locked_models=_PRIVATE.locked_models,
            )
        )

    assert series() == series()

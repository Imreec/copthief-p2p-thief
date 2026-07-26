"""Arena aggregation + champion regression gate (TODO M3-6; PLAN §8).

The gate logic is tested in BOTH directions here: green for a champion that tops its
role table, red (problems listed) for a pinned champion that lost — proving the CI
gate can actually fire (the M3-6 DoD's negative half).
"""

from copthief_core.domain.rules import Outcome
from copthief_core.sdk.arena import (
    ArenaReport,
    PairingSeries,
    build_report,
    champion_regression,
)
from copthief_core.strategy.referee import RefereeGameResult

CAPTURE, SURVIVAL = Outcome.COP_CAPTURE, Outcome.THIEF_SURVIVAL
SCORING = {"cop_capture": (20, 5), "thief_survival": (5, 10)}


def _series(police: str, thief: str, outcomes: list[Outcome]) -> PairingSeries:
    return PairingSeries(
        police_brain=police,
        thief_brain=thief,
        results=tuple(
            RefereeGameResult(seed=i, outcome=o, steps=5) for i, o in enumerate(outcomes)
        ),
    )


def _report() -> ArenaReport:
    # greedy police captures random twice; random police never captures anyone.
    return build_report(
        [
            _series("greedy", "random", [CAPTURE, CAPTURE, SURVIVAL]),
            _series("greedy", "greedy", [CAPTURE, SURVIVAL, SURVIVAL]),
            _series("random", "random", [SURVIVAL, SURVIVAL, SURVIVAL]),
            _series("random", "greedy", [SURVIVAL, SURVIVAL, SURVIVAL]),
        ],
        scores=dict(SCORING),
    )


def test_standings_count_wins_and_points_per_brain_and_role() -> None:
    report = _report()
    greedy_police = report.standing("greedy", "police")
    assert greedy_police.games == 6
    assert greedy_police.wins == 3  # three captures across its two police series
    assert greedy_police.points == 3 * 20 + 3 * 5
    random_thief = report.standing("random", "thief")
    assert random_thief.games == 6
    assert random_thief.wins == 4  # survivals against both cops
    assert random_thief.points == 2 * 5 + 4 * 10


def test_standings_sort_best_first_within_each_role() -> None:
    report = _report()
    police_rows = [s for s in report.standings if s.role == "police"]
    assert police_rows[0].brain == "greedy"
    assert police_rows[0].points >= police_rows[1].points


def test_champion_gate_green_when_the_champion_tops_its_role() -> None:
    # greedy tops both role tables in this synthetic report (police 75, thief 55).
    problems = champion_regression(_report(), {"police": "greedy", "thief": "greedy"})
    assert problems == []


def test_champion_gate_red_when_a_pinned_champion_lost_its_role() -> None:
    problems = champion_regression(_report(), {"police": "random", "thief": "random"})
    assert problems  # the gate names the dethroning
    assert any("police" in p and "greedy" in p for p in problems)


def test_champion_gate_red_for_an_unknown_champion_name() -> None:
    problems = champion_regression(_report(), {"police": "ghost", "thief": "random"})
    assert any("ghost" in p for p in problems)


def test_round_robin_threads_the_config_model_and_per_entry_feeds() -> None:
    """M7-14 end-to-end: a book-v1 arena with a lag-fed evader entry runs, stays
    deterministic, and gives every pairing one result per seed."""
    from pathlib import Path

    from copthief_core.sdk.arena import run_round_robin
    from copthief_core.sdk.arena_config import ArenaConfig, RosterEntry
    from copthief_core.sdk.simulation import SimulationSdk

    config = ArenaConfig(
        version="1.00",
        police_roster=(RosterEntry(name="greedy-manhattan", spec="greedy-manhattan"),),
        thief_roster=(RosterEntry(name="evader-lag1", spec="belief-evader", feed="truth-lag1"),),
        seeds=(1, 2),
        scenario_min_separation=4,
        brain_options={},
        dod_series=(),
        evidence_out="unused.md",
        scent_model="multiplicative_book_v1",
    )
    sdk = SimulationSdk(Path("config"))
    first = run_round_robin(sdk, config=config)
    second = run_round_robin(sdk, config=config)
    assert first == second
    assert len(first.series) == 1
    assert len(first.series[0].results) == 2
    assert first.standing("evader-lag1", "thief").games == 2
    # The doors must not be decorative: silently ignoring the feed or the model
    # would leave this identical to the shipped-defaults run of the same roster.
    from dataclasses import replace

    plain = replace(
        config,
        scent_model=None,
        thief_roster=(RosterEntry(name="evader-lag1", spec="belief-evader"),),
    )
    baseline = run_round_robin(sdk, config=plain)
    assert baseline != first

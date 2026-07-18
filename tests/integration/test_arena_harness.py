"""M3-6 DoD: the arena runs a seeded round-robin through the sdk, reproducibly,
and the shipped champion pin passes the regression gate (CI-blocking both ways —
the negative direction is proven in tests/unit/sdk/test_arena.py)."""

from pathlib import Path

from copthief_core.sdk.arena import champion_regression, load_champions, run_round_robin
from copthief_core.sdk.simulation import SimulationSdk

ROSTER = ("random", "greedy-manhattan")
SEEDS = range(1, 9)


def _sdk() -> SimulationSdk:
    return SimulationSdk(Path("config"))


def test_round_robin_covers_every_pairing_with_every_seed() -> None:
    report = run_round_robin(_sdk(), roster=ROSTER, seeds=SEEDS)
    assert len(report.series) == len(ROSTER) ** 2
    for series in report.series:
        assert len(series.results) == len(SEEDS)
    roles = {(s.brain, s.role) for s in report.standings}
    assert roles == {(b, r) for b in ROSTER for r in ("police", "thief")}


def test_round_robin_is_seed_reproducible() -> None:
    first = run_round_robin(_sdk(), roster=ROSTER, seeds=SEEDS)
    again = run_round_robin(_sdk(), roster=ROSTER, seeds=SEEDS)
    assert first == again


def test_shipped_champion_pin_passes_the_regression_gate() -> None:
    report = run_round_robin(_sdk(), roster=ROSTER, seeds=SEEDS)
    champions = load_champions(Path("config") / "arena_champion.json")
    assert champion_regression(report, champions) == []

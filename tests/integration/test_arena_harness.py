"""Arena round-robin + champion gate over the per-repo config (M3-6/M5-2; PLAN §8).

Config-driven since M5-2: rosters, seeds, and options come from `config/arena.json`
(per-repo — the mirrored copy of this test exercises whatever the local repo ships,
never a role name; PR #29 rule). The shipped champion pin must pass the regression
gate on the shipped roster — CI-blocking in both directions (the gate's negative half
is proven in tests/unit/sdk/test_arena.py).
"""

from pathlib import Path

from copthief_core.sdk.arena import champion_regression, load_champions, run_round_robin
from copthief_core.sdk.arena_config import load_arena_config
from copthief_core.sdk.simulation import SimulationSdk

CONFIG = load_arena_config(Path("config") / "arena.json")


def _sdk() -> SimulationSdk:
    return SimulationSdk(Path("config"))


def test_every_roster_entry_has_a_standing_in_its_role() -> None:
    report = run_round_robin(_sdk(), config=CONFIG)
    assert len(report.series) == len(CONFIG.police_roster) * len(CONFIG.thief_roster)
    for entry in CONFIG.police_roster:
        assert report.standing(entry.name, "police").games > 0
    for entry in CONFIG.thief_roster:
        assert report.standing(entry.name, "thief").games > 0


def test_round_robin_is_reproducible_on_the_shipped_config() -> None:
    first = run_round_robin(_sdk(), config=CONFIG)
    again = run_round_robin(_sdk(), config=CONFIG)
    assert first == again


def test_shipped_champion_pin_passes_the_regression_gate() -> None:
    report = run_round_robin(_sdk(), config=CONFIG)
    champions = load_champions(Path("config") / "arena_champion.json")
    assert champion_regression(report, champions) == []

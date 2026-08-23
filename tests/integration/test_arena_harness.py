"""Arena round-robin + champion gate over the per-repo config (M3-6/M5-2; PLAN §8).

Config-driven since M5-2: rosters, seeds, and options come from `config/arena.json`
(per-repo — the mirrored copy of this test exercises whatever the local repo ships,
never a role name; PR #29 rule). The shipped champion pin must pass the regression
gate on the shipped roster — CI-blocking in both directions (the gate's negative half
is proven in tests/unit/sdk/test_arena.py).
"""

from dataclasses import replace
from pathlib import Path

import pytest

from copthief_core.sdk.arena import (
    ArenaReport,
    champion_regression,
    load_champions,
    run_round_robin,
)
from copthief_core.sdk.arena_config import load_arena_config
from copthief_core.sdk.simulation import SimulationSdk

# Post-league (ADR-0018): the round robin is a strategy-measurement eval, not a code
# gate - it runs on demand via the arena workflow, mandatory before merging any
# change that touches a brain, a weight table, or the referee.
pytestmark = pytest.mark.arena

CONFIG = load_arena_config(Path("config") / "arena.json")


def _sdk() -> SimulationSdk:
    return SimulationSdk(Path("config"))


@pytest.fixture(scope="module")
def shipped_report() -> ArenaReport:
    """ONE round robin for the whole module (M9 CI profile: three tests each
    recomputed it, ~48s apiece — the fixture pays once; the reproducibility test
    pays its deliberate second). Keep the module on one xdist worker via
    --dist loadscope or the sharing is lost."""
    return run_round_robin(_sdk(), config=CONFIG)


def test_every_roster_entry_has_a_standing_in_its_role(shipped_report: ArenaReport) -> None:
    assert len(shipped_report.series) == len(CONFIG.police_roster) * len(CONFIG.thief_roster)
    for entry in CONFIG.police_roster:
        assert shipped_report.standing(entry.name, "police").games > 0
    for entry in CONFIG.thief_roster:
        assert shipped_report.standing(entry.name, "thief").games > 0


def test_round_robin_is_reproducible_on_the_shipped_rosters() -> None:
    """Determinism, proven twice on a reduced seed set — NOT a second full robin.

    The M11 CI-timeout postmortem: the shipped robin now runs the ARMED brains
    (k-wall forecast per doctrine decision), and under coverage a second full
    robin pushed the loadscope worker past the quality lane's cap. Determinism
    is an engine property; two seeds over the full shipped rosters/options prove
    it at a quarter of the cost, while the champion gate keeps the full robin
    (computed once, in the module fixture)."""
    reduced = replace(CONFIG, seeds=tuple(CONFIG.seeds[:2]))
    assert run_round_robin(_sdk(), config=reduced) == run_round_robin(_sdk(), config=reduced)


def test_shipped_champion_pin_passes_the_regression_gate(shipped_report: ArenaReport) -> None:
    champions = load_champions(Path("config") / "arena_champion.json")
    assert champion_regression(shipped_report, champions) == []

"""The configured DoD series (M5-2/M5-3; PLAN §13 M5): win-rate floors, CI-blocking.

Each `dod_series` entry in `config/arena.json` pins a head-to-head scenario series and
a minimum win-rate for one role — the ≥60%-vs-reference-heuristic exit criterion runs
here as a permanent regression once the role brain lands (this repo configures its own
role's entries; the mirrored copy runs whatever the local config lists — PR #29 rule).
"""

from pathlib import Path

import pytest

from copthief_core.domain.rules import Outcome
from copthief_core.sdk.arena_config import load_arena_config
from copthief_core.sdk.simulation import SimulationSdk
from copthief_core.strategy.scenarios import scenario_suite

CONFIG = load_arena_config(Path("config") / "arena.json")


@pytest.mark.skipif(not CONFIG.dod_series, reason="no DoD series configured yet")
def test_every_configured_dod_series_clears_its_win_rate_floor() -> None:
    sdk = SimulationSdk(Path("config"))
    for series in CONFIG.dod_series:
        scenarios = scenario_suite(
            sdk.constitution,
            seeds=series.seeds,
            min_separation=CONFIG.scenario_min_separation,
        )
        results = sdk.scenario_series(
            police=CONFIG.spec_for(series.police),
            thief=CONFIG.spec_for(series.thief),
            scenarios=scenarios,
            police_options=CONFIG.options_for(series.police),
            thief_options=CONFIG.options_for(series.thief),
        )
        winning = Outcome.COP_CAPTURE if series.wins_role == "police" else Outcome.THIEF_SURVIVAL
        rate = sum(r.outcome is winning for r in results) / len(results)
        assert rate >= series.min_win_rate, (
            f"{series.label}: {series.wins_role} win-rate {rate:.2f} "
            f"below the configured floor {series.min_win_rate}"
        )

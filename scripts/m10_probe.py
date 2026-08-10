"""Signed-start probe for the M10 counter-tune (throwaway instrument, not CI).

Plays single games on the SIGNED starts — the geometry the 08-10 friendly was
actually played on — and prints outcome/steps/barriers, so the tuning loop reads
the live-relevant row instead of the random-start aggregate. Not part of any gate.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from copthief_core.sdk.arena_config import load_arena_config  # noqa: E402
from copthief_core.sdk.simulation import SimulationSdk  # noqa: E402
from copthief_core.strategy.scenarios import Scenario  # noqa: E402

CONFIG = load_arena_config(Path("config/arena_m10_vibecode.json"))
sdk = SimulationSdk(Path("config"))
signed = Scenario(
    seed=0,
    cop_start=sdk.constitution.board.cop_start,
    thief_start=sdk.constitution.board.thief_start,
)


def probe(police: str, thief: str, seeds: range) -> None:
    results = []
    for seed in seeds:
        scenario = Scenario(seed=seed, cop_start=signed.cop_start, thief_start=signed.thief_start)
        game = sdk.scenario_series(
            police=CONFIG.spec_for(police),
            thief=CONFIG.spec_for(thief),
            scenarios=[scenario],
            police_options=CONFIG.options_for(police),
            thief_options=CONFIG.options_for(thief),
            police_feed=next(e.feed for e in CONFIG.police_roster if e.name == police),
            thief_feed=next(e.feed for e in CONFIG.thief_roster if e.name == thief),
            claim_threshold=CONFIG.claim_threshold_for(police),
            thief_claim_feed=next(e.claim_feed for e in CONFIG.thief_roster if e.name == thief),
        )[0]
        results.append(game)
    caps = sum(1 for g in results if g.outcome.value == "cop_capture")
    steps = [g.steps for g in results]
    walls = [g.barriers_placed for g in results]
    print(f"{police} vs {thief}: {caps}/{len(results)} captures, steps={steps}, walls={walls}")


if __name__ == "__main__":
    for police in ("police-m9", "police-m10"):
        probe(police, "vibecode-thief", range(1, 9))
    for thief in ("doctrine-m9", "doctrine-m10"):
        probe("vibecode-police", thief, range(1, 9))

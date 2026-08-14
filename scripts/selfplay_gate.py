"""Real-opponent pool gate for the self-play loop (M11 part 2; instrument, not CI).

The failure mode this file exists to catch: a harvested policy that beats our
own champion while losing to real opponents. Every GA round's candidate is
played against EVERY opposing arm of the refreshed pool (`config/arena_pool.json`)
over the pool's scenario suite, next to the incumbent champion on the identical
suite; the candidate ships only if it holds-or-improves on every arm.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from copthief_core.domain.rules import Outcome  # noqa: E402
from copthief_core.sdk.arena_config import ArenaConfig  # noqa: E402
from copthief_core.sdk.simulation import SimulationSdk  # noqa: E402
from copthief_core.strategy.scenarios import Scenario  # noqa: E402

GateRow = tuple[str, int, int, bool]  # (rival arm, champion wins, candidate wins, holds)


def _wins(
    sdk: SimulationSdk,
    pool: ArenaConfig,
    scenarios: list[Scenario],
    *,
    role: str,
    spec: str,
    feed: str,
    options: Mapping[str, float],
    rival: str,
    claim_threshold: float | None,
    claim_feed: str | None,
) -> int:
    """One contender's wins as `role` against one pool arm over the gate suite."""
    rivals = pool.police_roster if role == "thief" else pool.thief_roster
    entry = next(e for e in rivals if e.name == rival)
    police = entry.spec if role == "thief" else spec
    thief = spec if role == "thief" else entry.spec
    results = sdk.scenario_series(
        police=police,
        thief=thief,
        scenarios=scenarios,
        police_options=pool.options_for(rival) if role == "thief" else options,
        thief_options=options if role == "thief" else pool.options_for(rival),
        police_feed=entry.feed if role == "thief" else feed,
        thief_feed=feed if role == "thief" else entry.feed,
        claim_threshold=(pool.claim_threshold_for(rival) if role == "thief" else claim_threshold),
        thief_claim_feed=(claim_feed if role == "thief" else entry.claim_feed),
    )
    winning = Outcome.THIEF_SURVIVAL if role == "thief" else Outcome.COP_CAPTURE
    return sum(r.outcome is winning for r in results)


def pool_gate(
    sdk: SimulationSdk,
    pool: ArenaConfig,
    scenarios: list[Scenario],
    *,
    role: str,
    spec: str,
    feed: str,
    champion: Mapping[str, float],
    candidate: Mapping[str, float],
    claim_threshold: float | None,
    claim_feed: str | None,
) -> tuple[list[GateRow], bool]:
    """Candidate vs champion across every opposing pool arm (Input: the pool
    config + both option vectors; Output: per-arm rows + the all-green flag).
    Hold-or-improve is per arm — one regression anywhere refuses the harvest."""
    rivals = pool.police_roster if role == "thief" else pool.thief_roster
    rows: list[GateRow] = []
    for entry in rivals:
        shared = {
            "role": role,
            "spec": spec,
            "feed": feed,
            "rival": entry.name,
            "claim_threshold": claim_threshold,
            "claim_feed": claim_feed,
        }
        champ = _wins(sdk, pool, scenarios, options=champion, **shared)
        cand = _wins(sdk, pool, scenarios, options=candidate, **shared)
        rows.append((entry.name, champ, cand, cand >= champ))
    return rows, all(hold for _, _, _, hold in rows)

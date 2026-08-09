"""The police roster entry's `feed` must reach the series (M9 arena-door fix).

Found during the M9 study: `run_round_robin` honored only the THIEF entry's
feed — a police arm configured with 'sharp199' silently ran on the default
hidden feed, and its measured numbers were the control arm's. The pin records
both sides' feeds arriving at the series call.
"""

from typing import Any

from copthief_core.sdk.arena import run_round_robin
from copthief_core.sdk.arena_config import ArenaConfig, RosterEntry


class _RecordingSdk:
    """Stands in for SimulationSdk: records every series call's kwargs."""

    def __init__(self) -> None:
        from pathlib import Path

        from copthief_core.shared.config import load_all

        self.constitution, _p, _l = load_all(Path("config"), counted=False)
        self.calls: list[dict[str, Any]] = []

    def scenario_series(self, **kwargs: Any) -> list[Any]:  # noqa: ANN401 - recording stub
        self.calls.append(kwargs)
        return []


def test_both_sides_feeds_reach_the_series() -> None:
    config = ArenaConfig(
        version="1.00",
        police_roster=(RosterEntry(name="cop", spec="greedy-manhattan", feed="sharp199"),),
        thief_roster=(RosterEntry(name="rob", spec="greedy-manhattan", feed="truth-lag1"),),
        seeds=(1,),
        scenario_min_separation=4,
        brain_options={},
        dod_series=(),
        evidence_out="unused.md",
        champion_pin=None,
    )
    sdk = _RecordingSdk()
    run_round_robin(sdk, config=config)  # type: ignore[arg-type]
    assert sdk.calls, "the round robin made no series calls"
    call = sdk.calls[0]
    assert call["police_feed"] == "sharp199"
    assert call["thief_feed"] == "truth-lag1"

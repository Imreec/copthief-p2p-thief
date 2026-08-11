"""M11 tuning experiment runner (throwaway, not CI): doctrine variants vs police-m10.

Edit VARIANTS, run `uv run python scripts/m11_experiment.py [--full]`.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from copthief_core.sdk.simulation import SimulationSdk  # noqa: E402
from copthief_core.strategy.scenarios import Scenario, scenario_suite  # noqa: E402

sdk = SimulationSdk(Path("config"))
SIGNED = (sdk.constitution.board.cop_start, sdk.constitution.board.thief_start)
POLICE_OPTS = {
    "barrier_gain_threshold": 4.7893,
    "p_commit": 0.2,
    "w_budget": 1.7277,
    "w_distance": 3.8875,
    "w_mobility": 3.6061,
    "w_region": 0.1143,
    "tie_epsilon": 0.25,
    "contain_enabled": 1.0,
}

BASE = {
    "room_first": 1.0,
    "cage_escape": 1.0,
    "forecast_walls": 3.0,
    "forecast_wall_reach": 2.0,
}

ORBIT = {**BASE, "flight_floor": 2.0, "center_margin_cap": 2.0}
VARIANTS: dict[str, dict[str, float]] = {
    "orbit (armed)    ": dict(ORBIT),
}


def scenarios(full: bool) -> list[Scenario]:
    if full:
        return list(scenario_suite(sdk.constitution, seeds=range(1, 33), min_separation=4))
    return [Scenario(seed=seed, cop_start=SIGNED[0], thief_start=SIGNED[1]) for seed in range(1, 9)]


def run(label: str, thief_opts: dict[str, float], suite: list[Scenario]) -> None:
    results = [
        sdk.scenario_series(
            police="copthief_police.brain:PoliceBrain",
            thief="copthief_core.strategy.doctrine_evader:DoctrineEvaderBrain",
            scenarios=[sc],
            police_options=POLICE_OPTS,
            thief_options=thief_opts,
            police_feed="sharp199",
            thief_feed="sharp199",
        )[0]
        for sc in suite
    ]
    caps = sum(1 for g in results if g.outcome.value == "cop_capture")
    steps = [g.steps for g in results]
    walls = [g.barriers_placed for g in results]
    print(f"{label}: {caps}/{len(results)} captures, steps={steps}, walls={walls}")


def trace(variant: str, seed: int) -> None:
    from copthief_core.strategy.brains import make_brain
    from copthief_core.strategy.info_feed import make_feed
    from copthief_core.strategy.referee import play_referee_game

    class _Tap:
        def __init__(self, feed: object, track: list) -> None:
            self._feed, self._track = feed, track

        def observe(self, belief, *, trail, truth, board):  # noqa: ANN001, ANN201, ANN202
            self._track.append((truth, len(board.barriers)))
            return self._feed.observe(belief, trail=trail, truth=truth, board=board)

    trust = sdk.private.smell_trust_weight
    thief_track: list = []
    cop_track: list = []
    result = play_referee_game(
        sdk.constitution,
        police_brain=make_brain(
            "copthief_police.brain:PoliceBrain", seed=2 * seed, options=POLICE_OPTS
        ),
        thief_brain=make_brain(
            "copthief_core.strategy.doctrine_evader:DoctrineEvaderBrain",
            seed=2 * seed + 1,
            options=VARIANTS[variant],
        ),
        smell_trust=trust,
        seed=seed,
        cop_start=SIGNED[0],
        thief_start=SIGNED[1],
        belief_feed=_Tap(make_feed("sharp199", sdk.constitution, smell_trust=trust), thief_track),
        thief_belief_feed=_Tap(
            make_feed("sharp199", sdk.constitution, smell_trust=trust), cop_track
        ),
    )
    print(
        f"== seed {seed}: {result.outcome.value} @ {result.steps}, walls {result.barriers_placed}"
    )
    print("thief:", " ".join(f"{s + 1}:{c}" for s, (c, _b) in enumerate(thief_track)))
    print("cop  :", " ".join(f"{s + 1}:{c}w{b}" for s, (c, b) in enumerate(cop_track)))


if __name__ == "__main__":
    if sys.argv[1:2] == ["--trace"]:
        trace(sys.argv[2], int(sys.argv[3]))
    else:
        suite = scenarios("--full" in sys.argv)
        for label, opts in VARIANTS.items():
            run(label, opts, suite)

"""Trajectory trace for the M10 tuning loop (throwaway instrument, not CI).

Wraps both information feeds — each observes the mover's TRUE post-move cell —
so one referee game yields both tracks plus wall placements, without touching
the referee. Reads the m10 arena config for options/feeds. Not part of any gate.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from copthief_core.sdk.arena_config import load_arena_config  # noqa: E402
from copthief_core.sdk.simulation import SimulationSdk  # noqa: E402
from copthief_core.strategy.brains import make_brain  # noqa: E402
from copthief_core.strategy.info_feed import make_feed  # noqa: E402
from copthief_core.strategy.referee import play_referee_game  # noqa: E402
from copthief_core.strategy.referee_claims import ClaimPolicy  # noqa: E402


class _Tap:
    def __init__(self, feed: object, track: list) -> None:
        self._feed, self._track = feed, track

    def observe(self, belief, *, trail, truth, board):  # noqa: ANN001, ANN201, ANN202
        self._track.append((truth, len(board.barriers)))
        return self._feed.observe(belief, trail=trail, truth=truth, board=board)


def trace(police: str, thief: str, seed: int) -> None:
    config = load_arena_config(Path("config/arena_m10_vibecode.json"))
    sdk = SimulationSdk(Path("config"))
    constitution, trust = sdk.constitution, sdk.private.smell_trust_weight
    thief_track: list = []
    cop_track: list = []

    def feed_for(name: str | None, track: list) -> _Tap:
        return _Tap(make_feed(name or "hidden", constitution, smell_trust=trust), track)

    police_entry = next(e for e in config.police_roster if e.name == police)
    thief_entry = next(e for e in config.thief_roster if e.name == thief)
    result = play_referee_game(
        constitution,
        police_brain=make_brain(
            config.spec_for(police), seed=2 * seed, options=config.options_for(police)
        ),
        thief_brain=make_brain(
            config.spec_for(thief), seed=2 * seed + 1, options=config.options_for(thief)
        ),
        smell_trust=trust,
        seed=seed,
        belief_feed=feed_for(police_entry.feed, thief_track),
        thief_belief_feed=feed_for(thief_entry.feed, cop_track),
        thief_claim_feed=(
            feed_for(thief_entry.claim_feed, cop_track) if thief_entry.claim_feed else None
        ),
        claim_policy=ClaimPolicy(threshold=police_entry.claim_threshold),
    )
    print(
        f"== {police} vs {thief} seed {seed}: {result.outcome.value} @ {result.steps}, "
        f"walls {result.barriers_placed}"
    )
    print("thief:", " ".join(f"{s + 1}:{c}" for s, (c, _b) in enumerate(thief_track)))
    print("cop  :", " ".join(f"{s + 1}:{c}w{b}" for s, (c, b) in enumerate(cop_track)))


if __name__ == "__main__":
    trace(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 1)

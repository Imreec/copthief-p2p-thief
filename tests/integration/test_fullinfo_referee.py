"""Full-information referee games through the feed seam (wire-shape balance A/B).

The same loop, scenario suite, and brains as the shipped arena — only the information
structure differs. Role-blind: core brain names only (the mirrored copy must pass in
both repos, PR #29 rule). Strength CLAIMS live in the committed balance table, not
here; these tests pin determinism and the seam's plumb-through.
"""

from pathlib import Path

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import Board, Coord
from copthief_core.domain.scent import ScentField
from copthief_core.sdk.simulation import SimulationSdk
from copthief_core.strategy.info_feed import TruthFeed
from copthief_core.strategy.scenarios import scenario_suite

SEEDS = (1, 2, 3, 4)
SEPARATION = 4


class _MirrorFeed(TruthFeed):
    """A deliberately misleading feed: certainty at the point-reflected cell. If the
    brains truly consume the fed belief, play must diverge from the hidden baseline
    (TruthFeed itself may legitimately coincide with it — honest scent already marks
    the true cell on the shipped config, which is the balance table's finding)."""

    def observe(
        self, belief: BeliefFilter, *, trail: ScentField, truth: Coord, board: Board
    ) -> BeliefFilter:
        far = 2 * board.axis_start_index + board.grid_size - 1
        return super().observe(
            belief, trail=trail, truth=(far - truth[0], far - truth[1]), board=board
        )


def _sdk() -> SimulationSdk:
    return SimulationSdk(Path("config"))


def test_fullinfo_series_runs_and_is_reproducible() -> None:
    sdk = _sdk()
    feed = TruthFeed(sdk.constitution, smell_trust=sdk.private.smell_trust_weight)
    scenarios = scenario_suite(sdk.constitution, seeds=SEEDS, min_separation=SEPARATION)
    first = sdk.scenario_series(
        police="greedy-manhattan", thief="random", scenarios=scenarios, belief_feed=feed
    )
    again = sdk.scenario_series(
        police="greedy-manhattan", thief="random", scenarios=scenarios, belief_feed=feed
    )
    assert first == again
    assert len(first) == len(SEEDS)


def test_brains_consume_the_fed_belief_end_to_end() -> None:
    sdk = _sdk()
    feed = _MirrorFeed(sdk.constitution, smell_trust=sdk.private.smell_trust_weight)
    scenarios = scenario_suite(sdk.constitution, seeds=SEEDS, min_separation=SEPARATION)
    hidden = sdk.scenario_series(police="greedy-manhattan", thief="random", scenarios=scenarios)
    misled = sdk.scenario_series(
        police="greedy-manhattan", thief="random", scenarios=scenarios, belief_feed=feed
    )
    # Same seeds, same brains: a cop chasing the reflected cell cannot play the same
    # games as the hidden baseline — proves the seam feeds the decisions, not a copy.
    assert hidden != misled


def test_default_feed_is_byte_identical_to_the_legacy_hidden_path() -> None:
    sdk = _sdk()
    scenarios = scenario_suite(sdk.constitution, seeds=SEEDS, min_separation=SEPARATION)
    legacy = sdk.scenario_series(police="greedy-manhattan", thief="random", scenarios=scenarios)
    explicit_none = sdk.scenario_series(
        police="greedy-manhattan", thief="random", scenarios=scenarios, belief_feed=None
    )
    assert legacy == explicit_none

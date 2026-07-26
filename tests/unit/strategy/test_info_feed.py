"""Belief information feeds (wire-shape seam, kit issue #6): ScentFeed vs TruthFeed.

ScentFeed must reproduce the historical referee seam byte-for-byte (hidden positions,
reference-v3); TruthFeed must hand every brain a certainty delta at the opponent's
revealed cell (common knowledge, bookletter-v3). Role-blind: core brains only.
"""

from pathlib import Path

from copthief_core.shared.config import load_all
from copthief_core.strategy.info_feed import ScentFeed, TruthFeed
from copthief_core.strategy.referee_setup import referee_belief, referee_trail

CONSTITUTION, PRIVATE, _LIMITS = load_all(Path("config"), counted=False)
TRUST = PRIVATE.smell_trust_weight


def test_truth_feed_returns_a_certainty_delta_at_the_revealed_cell() -> None:
    board = CONSTITUTION.board.make_board()
    belief = referee_belief(CONSTITUTION, start=CONSTITUTION.board.thief_start, smell_trust=TRUST)
    truth = (2, 3)
    fed = TruthFeed(CONSTITUTION, smell_trust=TRUST).observe(
        belief, trail=referee_trail(CONSTITUTION), truth=truth, board=board
    )
    assert fed.probs() == {truth: 1.0}
    assert fed.argmax() == truth
    assert fed.belief_error(truth) == 0.0


def test_truth_feed_tracks_the_mover_across_observes() -> None:
    board = CONSTITUTION.board.make_board()
    feed = TruthFeed(CONSTITUTION, smell_trust=TRUST)
    trail = referee_trail(CONSTITUTION)
    belief = referee_belief(CONSTITUTION, start=(0, 0), smell_trust=TRUST)
    for truth in ((1, 0), (1, 1), (2, 1)):
        belief = feed.observe(belief, trail=trail, truth=truth, board=board)
        assert belief.probs() == {truth: 1.0}


def test_scent_feed_matches_the_legacy_predict_then_scent_seam() -> None:
    board = CONSTITUTION.board.make_board()
    start = CONSTITUTION.board.thief_start
    intensity = CONSTITUTION.pheromones.center_intensity
    trail = referee_trail(CONSTITUTION)
    trail.deposit((start[0], start[1] + 1), intensity)
    trail.decay()
    via_feed = referee_belief(CONSTITUTION, start=start, smell_trust=TRUST)
    manually = referee_belief(CONSTITUTION, start=start, smell_trust=TRUST)
    returned = ScentFeed().observe(via_feed, trail=trail, truth=start, board=board)
    manually.predict()
    manually.update_scent(trail.snapshot())
    assert returned is via_feed  # the legacy seam mutates in place
    assert via_feed.probs() == manually.probs()


def test_lag_truth_feed_reveals_the_cell_k_observations_late() -> None:
    """The claim-reading counter (M7-14): each `caught: false` response hands the
    evader the claimer's cell one step late — modeled as delayed common knowledge."""
    from copthief_core.strategy.info_feed import LagTruthFeed

    board = CONSTITUTION.board.make_board()
    feed = LagTruthFeed(CONSTITUTION, smell_trust=TRUST, lag=1)
    trail = referee_trail(CONSTITUTION)
    start = (0, 0)
    belief = referee_belief(CONSTITUTION, start=start, smell_trust=TRUST)
    # First observe: only the current truth is known, and it is embargoed for one
    # step — the signed-start delta IS the lag-1 information, so it must survive.
    belief = feed.observe(belief, trail=trail, truth=(1, 0), board=board)
    assert belief.probs() == {start: 1.0}
    belief = feed.observe(belief, trail=trail, truth=(1, 1), board=board)
    assert belief.probs() == {(1, 0): 1.0}
    belief = feed.observe(belief, trail=trail, truth=(2, 1), board=board)
    assert belief.probs() == {(1, 1): 1.0}


def test_lag_truth_feed_builds_on_the_current_board() -> None:
    """Like TruthFeed, the delta must live on the CURRENT board so declared barriers
    shape the evader's motion model."""
    from copthief_core.strategy.info_feed import LagTruthFeed

    board = CONSTITUTION.board.make_board().with_barrier((3, 4))
    feed = LagTruthFeed(CONSTITUTION, smell_trust=TRUST, lag=1)
    trail = referee_trail(CONSTITUTION)
    belief = referee_belief(CONSTITUTION, start=(3, 3), smell_trust=TRUST)
    belief = feed.observe(belief, trail=trail, truth=(2, 3), board=board)
    belief = feed.observe(belief, trail=trail, truth=(1, 3), board=board)
    assert belief.probs() == {(2, 3): 1.0}
    belief.predict()
    assert (3, 4) not in belief.probs()


def test_make_feed_resolves_the_config_names() -> None:
    """Roster entries name their feed in config; the factory is the one resolver."""
    import pytest

    from copthief_core.strategy.info_feed import LagTruthFeed, make_feed

    assert isinstance(make_feed("hidden", CONSTITUTION, smell_trust=TRUST), ScentFeed)
    assert isinstance(make_feed("truth", CONSTITUTION, smell_trust=TRUST), TruthFeed)
    lagged = make_feed("truth-lag1", CONSTITUTION, smell_trust=TRUST)
    assert isinstance(lagged, LagTruthFeed)
    with pytest.raises(ValueError, match="unknown feed"):
        make_feed("psychic", CONSTITUTION, smell_trust=TRUST)

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

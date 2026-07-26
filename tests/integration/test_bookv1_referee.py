"""Referee games under a selected scent model + per-side feeds (M7-14).

Two doors the counted-series prep needs: the whole referee world (both trails, both
observation models) can run `multiplicative_book_v1`, and the two sides' information
structures can differ (the claim-reading counter is thief-side lag-1 truth while our
cop stays hidden-info). Determinism pins ride along — the arena's reproducibility
contract must survive both doors.
"""

from pathlib import Path

from copthief_core.shared.config import load_all
from copthief_core.shared.locked_models import build_scent_model
from copthief_core.strategy.brains import make_brain
from copthief_core.strategy.info_feed import ScentFeed, TruthFeed
from copthief_core.strategy.referee import play_referee_game
from copthief_core.strategy.scenarios import scenario_suite

CONSTITUTION, PRIVATE, _ = load_all(Path("config"), counted=False)
BOOK = build_scent_model(PRIVATE.locked_models, "multiplicative_book_v1", CONSTITUTION.pheromones)
SCENARIOS = scenario_suite(CONSTITUTION, seeds=range(1, 9), min_separation=4)


def _series(scent_model: object = None, thief_feed: object = None) -> list[tuple[str, int]]:
    """Varied seeded starts — one fixed start would collapse deterministic brains
    into eight copies of the same game and blind the divergence asserts."""
    results = []
    for scenario in SCENARIOS:
        game = play_referee_game(
            CONSTITUTION,
            police_brain=make_brain("greedy-manhattan", seed=2 * scenario.seed),
            thief_brain=make_brain("ref-thief", seed=2 * scenario.seed + 1),
            smell_trust=PRIVATE.smell_trust_weight,
            seed=scenario.seed,
            cop_start=scenario.cop_start,
            thief_start=scenario.thief_start,
            scent_model=scent_model,  # type: ignore[arg-type]
            thief_belief_feed=thief_feed,  # type: ignore[arg-type]
        )
        results.append((game.outcome.value, game.steps))
    return results


def test_book_model_games_are_deterministic() -> None:
    assert _series(scent_model=BOOK) == _series(scent_model=BOOK)


def test_the_selected_model_reaches_behavior() -> None:
    """If the book physics never changes a single game across eight seeds, the door
    is decorative — the M3-8 belief measurements say the two models disagree hard."""
    assert _series(scent_model=BOOK) != _series()


class _SpyFeed:
    """A recording ScentFeed: which side's observations flow through THIS feed."""

    def __init__(self) -> None:
        self.truths: list[tuple[int, int]] = []
        self._inner = ScentFeed()

    def observe(self, belief: object, *, trail: object, truth: object, board: object) -> object:
        self.truths.append(truth)  # type: ignore[arg-type]
        return self._inner.observe(belief, trail=trail, truth=truth, board=board)  # type: ignore[arg-type]


def test_the_thief_feed_can_differ_from_the_police_feed() -> None:
    """The asymmetric shape the trap-aware-evader measurement needs: a feed passed as
    `thief_belief_feed` sees ONLY the cop's truth stream, while the police side stays
    on the default hidden feed (an outcome fingerprint cannot pin this — a survival
    looks like a survival — so the wiring is spied directly)."""
    spy = _SpyFeed()
    scenario = SCENARIOS[0]
    game = play_referee_game(
        CONSTITUTION,
        police_brain=make_brain("greedy-manhattan", seed=2 * scenario.seed),
        thief_brain=make_brain("ref-thief", seed=2 * scenario.seed + 1),
        smell_trust=PRIVATE.smell_trust_weight,
        seed=scenario.seed,
        cop_start=scenario.cop_start,
        thief_start=scenario.thief_start,
        thief_belief_feed=spy,
    )
    # One cop-truth observation per cop ACTION — the thief's threshold move ends a
    # survival before the cop's final reply (wire-mirrored), so a 35-step survival
    # carries 34 cop actions. First truth sits one cop action from the cop start,
    # while the thief start is >= 4 Manhattan away (min_separation) — a thief truth
    # leaking into this feed would sit far from the cop start and fail loudly.
    assert game.outcome.value == "thief_survival"
    assert len(spy.truths) == game.steps - 1
    first = spy.truths[0]
    assert abs(first[0] - scenario.cop_start[0]) + abs(first[1] - scenario.cop_start[1]) <= 1
    assert abs(first[0] - scenario.thief_start[0]) + abs(first[1] - scenario.thief_start[1]) >= 2


def test_a_truth_thief_feed_still_composes_with_a_hidden_police_feed() -> None:
    """TruthFeed on the thief side only runs to completion and stays deterministic."""
    truth = TruthFeed(CONSTITUTION, smell_trust=PRIVATE.smell_trust_weight)
    assert _series(thief_feed=truth) == _series(thief_feed=truth)

"""SharpScentFeed (M9-2 arena door) — per-arm scoping of the fresh-peak tier.

The sharp decode must be scoped PER ROSTER ARM: modeled rivals keep the exact
filter their real code fields, while our arm plays the upgraded stack. The
feed grammar mirrors truth-lag<K>: 'sharp<T>' enables the tier at trust T.
"""

from pathlib import Path

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import Board
from copthief_core.domain.scent_models import SubtractiveChebyshevV1
from copthief_core.shared.config import load_all
from copthief_core.strategy.info_feed import ScentFeed, SharpScentFeed, make_feed

CONSTITUTION, _PRIVATE, _LIMITS = load_all(Path("config"), counted=False)

MOVE_SET = ("N", "S", "E", "W", "STAY")

MODEL = SubtractiveChebyshevV1(
    {
        "field_size": 5,
        "emit_intensity": 0.9,
        "min_center_intensity": 0.05,
        "decay_per_step": 0.1,
        "rounding_decimals": 3,
    }
)


class _StubTrail:
    """A trail stub: `snapshot` is the only surface the hidden feed reads."""

    def __init__(self, grid: dict[str, float]) -> None:
        self._grid = grid

    def snapshot(self) -> dict[str, float]:
        return self._grid


def test_sharp_feed_arms_the_decode_on_a_plain_filter() -> None:
    """The feed enables the tier on a filter built without it: the fresh stamp
    dominates the posterior after one observation."""
    board = Board(grid_size=7, axis_origin_corner="top-left", axis_start_index=0)
    belief = BeliefFilter(
        board=board,
        move_set=MOVE_SET,
        start=(3, 3),
        center_intensity=0.9,
        decay=0.1,
        smell_trust=4.0,
        hint_trust=0.0,
        scent_model=MODEL,
    )
    trail = _StubTrail({"3,4": 0.8, "3,3": 0.5, "2,4": 0.5})
    fed = SharpScentFeed(trust=199.0).observe(
        belief,
        trail=trail,  # type: ignore[arg-type]
        truth=(9, 9),
        board=board,
    )
    assert fed.prob_at((3, 4)) > 0.9


def test_make_feed_grammar_resolves_sharp() -> None:
    """'sharp<T>' mirrors 'truth-lag<K>': digits parse as the trust value."""
    feed = make_feed("sharp199", CONSTITUTION, smell_trust=4.0)
    assert isinstance(feed, SharpScentFeed)
    assert isinstance(make_feed("hidden", CONSTITUTION, smell_trust=4.0), ScentFeed)

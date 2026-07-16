"""Scoring table + series settlement (book ch.3 table 2; App F tables 17–18)."""

from copthief_core.domain.rules import Outcome
from copthief_core.domain.scoring import ScoringTable, score_mini_game, settle_series

TABLE = ScoringTable(
    capture_cop=20,
    capture_thief=5,
    survival_cop=5,
    survival_thief=10,
    tie_score=2,
    technical_loss=0,
)


def test_capture_pays_the_asymmetric_capture_row() -> None:
    assert score_mini_game(Outcome.COP_CAPTURE, TABLE) == (20, 5)


def test_survival_pays_the_asymmetric_survival_row() -> None:
    assert score_mini_game(Outcome.THIEF_SURVIVAL, TABLE) == (5, 10)


def test_technical_loss_zeroes_both_sides() -> None:
    assert score_mini_game(Outcome.TECHNICAL_LOSS, TABLE) == (0, 0)


def test_series_totals_accumulate_per_minigame_scores() -> None:
    scores = [(20, 5), (5, 10), (20, 5)]
    result = settle_series(scores, TABLE)
    assert (result.cop_total, result.thief_total) == (45, 20)
    assert not result.tied


def test_tied_series_awards_tie_score_to_each_side() -> None:
    scores = [(20, 5), (5, 10), (5, 10), (20, 5), (0, 0), (5, 10)]
    # raw totals: cop 55, thief 40 - not tied; build a genuinely tied series instead
    tied_scores = [(20, 5), (5, 10), (5, 10), (10, 15)]
    result = settle_series(tied_scores, TABLE)
    assert result.tied
    assert result.cop_total == result.thief_total == 40 + 2
    assert settle_series(scores, TABLE).tied is False


def test_empty_series_is_tied_at_tie_score_each() -> None:
    result = settle_series([], TABLE)
    assert result.tied
    assert result.cop_total == result.thief_total == 2

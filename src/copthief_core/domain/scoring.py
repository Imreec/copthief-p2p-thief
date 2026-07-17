"""Scoring (book ch.3 table 2; App F table 17): mini-game rows + series settlement.

Every value arrives from the signed config's `scoring` section — this module holds the
*shape* of the table, never its numbers. Totals are always derived from per-mini-game
outcomes, never declared (PRD FR-11; kit §6 "derived, not declared").
"""

from __future__ import annotations

from dataclasses import dataclass

from copthief_core.domain.rules import Outcome


@dataclass(frozen=True)
class ScoringTable:
    """The signed `scoring` section of `config/game.json` (all rows App F fixed)."""

    capture_cop: int
    capture_thief: int
    survival_cop: int
    survival_thief: int
    tie_score: int
    technical_loss: int


@dataclass(frozen=True)
class SeriesResult:
    """Settled series vs one opponent: derived totals and whether the tie rule fired."""

    cop_total: int
    thief_total: int
    tied: bool


def scores_for(outcome: str, table: ScoringTable) -> tuple[int, int]:
    """`score_mini_game` over the peer layer's internal outcome strings.

    "cop_capture" / "thief_survival" hit their table rows; anything else (timeout,
    incomplete, protocol violation) is the technical-loss row — 0/0 for both, matching
    the reference's scoring of non-capture/non-survival results.
    """
    named = {"cop_capture": Outcome.COP_CAPTURE, "thief_survival": Outcome.THIEF_SURVIVAL}
    return score_mini_game(named.get(outcome, Outcome.TECHNICAL_LOSS), table)


def score_mini_game(outcome: Outcome, table: ScoringTable) -> tuple[int, int]:
    """(cop points, thief points) for one mini-game outcome per the fixed table."""
    rows: dict[Outcome, tuple[int, int]] = {
        Outcome.COP_CAPTURE: (table.capture_cop, table.capture_thief),
        Outcome.THIEF_SURVIVAL: (table.survival_cop, table.survival_thief),
        Outcome.TECHNICAL_LOSS: (table.technical_loss, table.technical_loss),
    }
    return rows[outcome]


def settle_series(scores: list[tuple[int, int]], table: ScoringTable) -> SeriesResult:
    """Aggregate a series of per-mini-game (cop, thief) scores and apply the tie rule.

    App F table 17: when the aggregate score of all mini-games vs an opponent ties,
    each side scores `tie_score`. Interpretation (documented, M2-verified vs the
    reference): the award is ADDED to each side's equal total, settling the series
    without discarding earned points.
    """
    cop_total = sum(cop for cop, _ in scores)
    thief_total = sum(thief for _, thief in scores)
    if cop_total != thief_total:
        return SeriesResult(cop_total=cop_total, thief_total=thief_total, tied=False)
    return SeriesResult(
        cop_total=cop_total + table.tie_score,
        thief_total=thief_total + table.tie_score,
        tied=True,
    )

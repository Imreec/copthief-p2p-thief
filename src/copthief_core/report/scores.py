"""Per-group scoring + series aggregate for the result artifact (PRD_reporting §3).

DRY bridge, not new rules: wire-result vocabulary maps onto the SAME `domain/scoring`
table rows the rules engine uses, and the F7 tie interpretation (award ADDED to equal
totals, M2-verified) is applied per group here exactly as `settle_series` applies it
per role. The symmetric-outcome dict is the settlement contract: it carries only what
both peers derive identically — never per-peer tokens or wall-clock timestamps.
"""

from __future__ import annotations

from typing import Any

from copthief_core.domain.rules import Outcome
from copthief_core.domain.scoring import ScoringTable, score_mini_game

_WIRE_OUTCOMES = {"capture": Outcome.COP_CAPTURE, "survival": Outcome.THIEF_SURVIVAL}
SYMMETRIC_SUBGAME_KEYS = ("sub_game_number", "roles", "result", "winner_group", "score")


def subgame_score(result: str, roles: dict[str, str], table: ScoringTable) -> dict[str, int]:
    """Per-GROUP score dict for one sub-game (Input: wire result string + group->role
    map + the signed table; timeout/tamper/anything-else hits the technical-loss row)."""
    outcome = _WIRE_OUTCOMES.get(result, Outcome.TECHNICAL_LOSS)
    cop_points, thief_points = score_mini_game(outcome, table)
    return {gid: cop_points if role == "police" else thief_points for gid, role in roles.items()}


def aggregate_groups(sub_games: list[dict[str, Any]], tie_score: int) -> dict[str, Any]:
    """The result artifact's aggregate block over per-sub-game rows.

    Input: rows carrying `score`/`winner_group`/`tie`; Output: total_score,
    sub_games_won, ties (per-sub-game), winner_group (None on a series tie),
    series_tie — with `tie_score` ADDED to both equal totals (F7).
    """
    groups = list(sub_games[0]["score"])
    totals = {g: sum(sg["score"][g] for sg in sub_games) for g in groups}
    won = {g: sum(1 for sg in sub_games if sg["winner_group"] == g) for g in groups}
    ties = sum(1 for sg in sub_games if sg["tie"])
    series_tie = len(set(totals.values())) == 1
    if series_tie:
        totals = {g: total + tie_score for g, total in totals.items()}
        winner = None
    else:
        winner = max(totals, key=lambda g: totals[g])
    return {
        "total_score": totals,
        "sub_games_won": won,
        "ties": ties,
        "winner_group": winner,
        "series_tie": series_tie,
    }


def symmetric_outcome(
    game_id: str, aggregate: dict[str, Any], sub_games: list[dict[str, Any]]
) -> dict[str, Any]:
    """The dict under the result's mutual consensus signature: symmetric facts only,
    so both peers' independently-written result files carry the SAME hash."""
    return {
        "game_id": game_id,
        "aggregate": aggregate,
        "sub_games": [{key: sg[key] for key in SYMMETRIC_SUBGAME_KEYS} for sg in sub_games],
    }

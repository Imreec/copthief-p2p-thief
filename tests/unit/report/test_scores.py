"""Per-group scoring + series aggregate for the result artifact (PRD_reporting §3).

Reuses the domain ScoringTable rows (DRY: the report layer maps wire-result vocabulary
onto the same table `domain/scoring` serves — no duplicated numbers, no new rules).
"""

from __future__ import annotations

from copthief_core.domain.scoring import ScoringTable
from copthief_core.report.scores import aggregate_groups, subgame_score, symmetric_outcome

ROLES = {"team-a": "police", "team-b": "thief"}


def test_capture_pays_the_capture_row_to_the_police_group(table: ScoringTable) -> None:
    assert subgame_score("capture", ROLES, table) == {"team-a": 20, "team-b": 5}


def test_survival_pays_the_survival_row_to_each_role(table: ScoringTable) -> None:
    assert subgame_score("survival", ROLES, table) == {"team-a": 5, "team-b": 10}


def test_timeout_and_tamper_score_the_technical_loss_row_for_both(table: ScoringTable) -> None:
    assert subgame_score("timeout", ROLES, table) == {"team-a": 0, "team-b": 0}
    assert subgame_score("tamper_forfeit", ROLES, table) == {"team-a": 0, "team-b": 0}


def _sub_game(n: int, winner: str | None, score: dict[str, int]) -> dict[str, object]:
    return {"sub_game_number": n, "winner_group": winner, "tie": winner is None, "score": score}


def test_aggregate_groups_totals_wins_and_names_the_winner() -> None:
    sub_games = [
        _sub_game(1, "team-a", {"team-a": 20, "team-b": 5}),
        _sub_game(2, "team-b", {"team-a": 5, "team-b": 10}),
    ]
    aggregate = aggregate_groups(sub_games, tie_score=2)
    assert aggregate["total_score"] == {"team-a": 25, "team-b": 15}
    assert aggregate["sub_games_won"] == {"team-a": 1, "team-b": 1}
    assert aggregate["ties"] == 0
    assert aggregate["winner_group"] == "team-a"
    assert aggregate["series_tie"] is False


def test_series_tie_adds_tie_score_to_both_equal_totals() -> None:
    """F7 (M2-verified): the award is ADDED to each side's equal total."""
    sub_games = [
        _sub_game(1, "team-a", {"team-a": 20, "team-b": 5}),
        _sub_game(2, "team-b", {"team-a": 5, "team-b": 20}),
    ]
    aggregate = aggregate_groups(sub_games, tie_score=2)
    assert aggregate["total_score"] == {"team-a": 27, "team-b": 27}
    assert aggregate["winner_group"] is None
    assert aggregate["series_tie"] is True
    assert aggregate["ties"] == 0  # per-sub-game ties, not the series tie


def test_symmetric_outcome_carries_only_the_agreed_symmetric_keys() -> None:
    """The mutual signature hashes what both peers derive identically — never per-peer
    tokens or wall-clock timestamps (reference emit_series comment, @960499fd)."""
    sub_games = [
        {
            "sub_game_number": 1,
            "roles": ROLES,
            "result": "capture",
            "winner_group": "team-a",
            "score": {"team-a": 20, "team-b": 5},
            "started_at": "2026-07-19T10:00:00+00:00",
            "tokens": {"team-a": 7, "team-b": 0},
        }
    ]
    aggregate = {"total_score": {"team-a": 20, "team-b": 5}}
    symmetric = symmetric_outcome("gid", aggregate, sub_games)
    assert set(symmetric) == {"game_id", "aggregate", "sub_games"}
    assert set(symmetric["sub_games"][0]) == {
        "sub_game_number",
        "roles",
        "result",
        "winner_group",
        "score",
    }

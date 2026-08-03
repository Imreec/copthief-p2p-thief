"""M7-28/M7-33 pins: the result rows' `github_commit` columns (split from
test_emit, 150-line rule). Own column from the sealed step-0 (role-aware at the
seal); opponent column from their revealed step-0 riding the summary."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from report_fixtures import make_identity, make_summary

from copthief_core.domain.scoring import ScoringTable
from copthief_core.report.emit import emit_series


def test_emit_series_fills_our_own_github_commit_from_the_sealed_step0(
    tmp_path: Path, table: ScoringTable, shared_terms: dict[str, Any]
) -> None:
    """M7-28: the book mandates the exact commit played per sub-game in the closing
    email's JSON (ch.5 -> s9.3.3); our sealed step-0 already records it, so the result
    row reads it from there. The opponent column stays "unknown" until the proposed
    commit-in-negotiate declaration is agreed (their own report carries theirs)."""
    sha = "ab" * 20
    summaries = [
        make_summary(sub_game_number=1, role="thief", github_commit=sha),
        make_summary(
            sub_game_number=2,
            role="police",
            result="survival",
            winner="thief",
            github_commit=sha,
        ),
    ]
    result = emit_series(
        summaries=summaries,
        own_identity=make_identity("team-a", 8801),
        opponent_identity=make_identity("team-b", 8802),
        game_id="team-a-vs-team-b",
        game_uid="uid-1",
        shared_terms=shared_terms,
        terms={"rules": {"max_steps": 35}},
        table=table,
        out_root=tmp_path,
    )
    for row in result["sub_games"]:
        assert row["github_commit"] == {"team-a": sha, "team-b": "unknown"}


def test_emit_series_fills_the_opponent_commit_column_from_the_summary(
    tmp_path: Path, table: ScoringTable, shared_terms: dict[str, Any]
) -> None:
    """M7-33: the book's example result fills BOTH columns; the opponent's commit is
    read from their revealed step-0 at settlement and rides the summary."""
    theirs = "7cf3fc9"
    summary = make_summary(sub_game_number=1, role="thief", github_commit="ab" * 20)
    summary["opponent_github_commit"] = theirs
    result = emit_series(
        summaries=[summary],
        own_identity=make_identity("team-a", 8801),
        opponent_identity=make_identity("team-b", 8802),
        game_id="team-a-vs-team-b",
        game_uid="uid-1",
        shared_terms=shared_terms,
        terms={"rules": {"max_steps": 35}},
        table=table,
        out_root=tmp_path,
    )
    assert result["sub_games"][0]["github_commit"] == {"team-a": "ab" * 20, "team-b": theirs}

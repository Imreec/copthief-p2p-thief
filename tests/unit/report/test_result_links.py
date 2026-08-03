"""M7-39 pins: the four repo links in the result (rule 49 + book p.96), split from
test_league_fields (150-line rule)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from report_fixtures import make_identity, make_summary

from copthief_core.domain.scoring import ScoringTable
from copthief_core.report.emit import emit_series


def test_the_result_links_carry_all_four_repo_links(
    tmp_path: Path, table: ScoringTable, shared_terms: dict[str, Any]
) -> None:
    """M7-39 (rule 49 + book p.96): the game-end email's JSON carries the FOUR repo
    links — both teams' cop and thief repos — under links.github (the opponent
    team's shape, concurred; the reference sample has no such key, book-above-
    examples). Sourced from the two identities; an opponent that declared no repos
    gets {} — never invented."""
    own = make_identity("team-a", 8801)
    own["repos"] = {"cop": "https://x/a-cop", "thief": "https://x/a-thief"}
    opp = make_identity("team-b", 8802)
    opp["repos"] = {"cop": "https://x/b-cop", "thief": "https://x/b-thief"}
    result = emit_series(
        summaries=[make_summary(sub_game_number=1, role="thief")],
        own_identity=own,
        opponent_identity=opp,
        game_id="team-a-vs-team-b",
        game_uid="uid-1",
        shared_terms=shared_terms,
        terms={"rules": {"max_steps": 35}},
        table=table,
        out_root=tmp_path,
    )
    assert result["links"]["github"] == {
        "team-a": {"cop": "https://x/a-cop", "thief": "https://x/a-thief"},
        "team-b": {"cop": "https://x/b-cop", "thief": "https://x/b-thief"},
    }
    assert "S01R02" not in result["links"]["_remark"]  # the example-text leftover


def test_absent_opponent_repos_stay_empty_in_the_result_links(
    tmp_path: Path, table: ScoringTable, shared_terms: dict[str, Any]
) -> None:
    own = make_identity("team-a", 8801)
    own["repos"] = {"cop": "https://x/a-cop", "thief": "https://x/a-thief"}
    opp = make_identity("team-b", 8802)
    opp["repos"] = {}
    result = emit_series(
        summaries=[make_summary(sub_game_number=1, role="thief")],
        own_identity=own,
        opponent_identity=opp,
        game_id="team-a-vs-team-b",
        game_uid="uid-1",
        shared_terms=shared_terms,
        terms={"rules": {"max_steps": 35}},
        table=table,
        out_root=tmp_path,
    )
    assert result["links"]["github"]["team-b"] == {}

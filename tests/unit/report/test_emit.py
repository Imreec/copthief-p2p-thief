"""Series emission to disk (PRD_reporting §3): four artifacts + Hebrew reports.

Byte discipline: artifacts are written as UTF-8 LF bytes (never platform newlines —
ops gotcha #6), ``indent=2, ensure_ascii=False``, no trailing newline; every artifact
is schema-validated BEFORE it touches disk (PLAN §7).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from report_fixtures import make_identity, make_summary

from copthief_core.domain.scoring import ScoringTable
from copthief_core.report.consensus import consensus_signature
from copthief_core.report.emit import artifact_bytes, emit_series
from copthief_core.report.schemas import ReportValidationError
from copthief_core.report.scores import symmetric_outcome


def _emit(tmp_path: Path, table: ScoringTable, shared_terms: dict[str, Any]) -> dict[str, Any]:
    summaries = [
        make_summary(sub_game_number=1, role="thief", result="capture", winner="police"),
        make_summary(sub_game_number=2, role="police", result="survival", winner="thief"),
    ]
    return emit_series(
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


def test_emit_series_writes_all_artifacts_into_the_group_folder(
    tmp_path: Path, table: ScoringTable, shared_terms: dict[str, Any]
) -> None:
    _emit(tmp_path, table, shared_terms)
    names = sorted(p.name for p in (tmp_path / "team-a").iterdir())
    assert names == [
        "config_team-a-vs-team-b_g01.json",
        "config_team-a-vs-team-b_g02.json",
        "declaration_team-a-vs-team-b.json",
        "log_team-a-vs-team-b_g01.json",
        "log_team-a-vs-team-b_g02.json",
        "report_team-a-vs-team-b_g01.json",
        "report_team-a-vs-team-b_g02.json",
        "result_team-a-vs-team-b.json",
    ]


def test_emit_series_result_matches_the_file_and_signs_the_symmetric_outcome(
    tmp_path: Path, table: ScoringTable, shared_terms: dict[str, Any]
) -> None:
    result = _emit(tmp_path, table, shared_terms)
    on_disk = json.loads(
        (tmp_path / "team-a" / "result_team-a-vs-team-b.json").read_text(encoding="utf-8")
    )
    assert on_disk == result
    # The signed symmetric outcome covers the SHARED game facts only — tokens and the
    # M7-34 league fields (each side's own declarations) stay outside the preimage,
    # so two honest reports with different declared counts still verify.
    unsigned = {
        "tokens_total_series",
        "games_played_including_this",
        "first_meeting_between_groups",
        "diversity_reward_applied",
    }
    aggregate = {k: v for k, v in result["final_result"].items() if k not in unsigned}
    slim = [
        {key: sg[key] for key in ("sub_game_number", "roles", "result", "winner_group", "score")}
        for sg in result["sub_games"]
    ]
    rebuilt = symmetric_outcome("team-a-vs-team-b", aggregate, result["sub_games"])
    assert rebuilt["sub_games"] == slim
    assert result["mutual_agreement"]["sha256"] == consensus_signature(rebuilt)


def test_emit_series_subgame_rows_carry_commit_and_token_defaults(
    tmp_path: Path, table: ScoringTable, shared_terms: dict[str, Any]
) -> None:
    result = _emit(tmp_path, table, shared_terms)
    first = result["sub_games"][0]
    assert first["roles"] == {"team-a": "thief", "team-b": "police"}
    assert first["github_commit"] == {"team-a": "unknown", "team-b": "unknown"}  # no sealed hash
    assert first["tokens"] == {"team-a": 0, "team-b": 0}
    assert first["log_files"]["team-a"] == "log_team-a-vs-team-b_g01.json"  # sample-flat (M7-28)
    assert first["score"] == {"team-a": 5, "team-b": 20}
    second = result["sub_games"][1]
    assert second["roles"] == {"team-a": "police", "team-b": "thief"}
    assert second["score"] == {"team-a": 5, "team-b": 10}


def test_artifact_bytes_are_lf_utf8_indent2_without_trailing_newline() -> None:
    blob = artifact_bytes({"א": 1, "b": [1, 2]})
    assert blob == '{\n  "א": 1,\n  "b": [\n    1,\n    2\n  ]\n}'.encode()
    assert b"\r" not in blob
    assert not blob.endswith(b"\n")


def test_emit_series_refuses_an_invalid_summary_before_writing(
    tmp_path: Path, table: ScoringTable, shared_terms: dict[str, Any]
) -> None:
    broken = make_summary()
    del broken["audit"]
    with pytest.raises((ReportValidationError, KeyError)):
        emit_series(
            summaries=[broken],
            own_identity=make_identity("team-a", 8801),
            opponent_identity=make_identity("team-b", 8802),
            game_id="gid",
            game_uid="uid",
            shared_terms=shared_terms,
            terms={},
            table=table,
            out_root=tmp_path,
        )

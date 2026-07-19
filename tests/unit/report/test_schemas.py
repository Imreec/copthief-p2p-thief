"""Artifact naming grammar + pre-write validation (PRD_reporting §3; book App F naming)."""

from __future__ import annotations

import pytest

from copthief_core.report.schemas import (
    SCHEMA_VERSION,
    ReportValidationError,
    config_filename,
    declaration_filename,
    links,
    log_filename,
    report_filename,
    result_filename,
    validate_artifact,
)


def test_filenames_derive_from_game_id_with_zero_padded_subgame() -> None:
    gid = "S01R02-team07-vs-team13"
    assert declaration_filename(gid) == f"declaration_{gid}.json"
    assert result_filename(gid) == f"result_{gid}.json"
    assert config_filename(gid, 1) == f"config_{gid}_g01.json"
    assert log_filename(gid, 12) == f"log_{gid}_g12.json"
    assert report_filename(gid, 3) == f"report_{gid}_g03.json"


def test_links_block_keeps_literal_gnn_placeholder_for_per_subgame_files() -> None:
    block = links("gid-x")
    assert block["declaration"] == "declaration_gid-x.json"
    assert block["result"] == "result_gid-x.json"
    assert block["config"] == "config_gid-x_g<NN>.json"
    assert block["log"] == "log_gid-x_g<NN>.json"
    assert isinstance(block["_remark"], str)
    assert block["_remark"]


def test_schema_version_is_the_reference_generation() -> None:
    assert SCHEMA_VERSION == "1.1"


def test_validate_artifact_accepts_a_complete_result_shell() -> None:
    data = {
        "_schema": "s",
        "schema_version": SCHEMA_VERSION,
        "report_type": "final_game_result",
        "game_id": "g",
        "game_uid": "u",
        "links": links("g"),
        "timezone": "Asia/Jerusalem",
        "groups": ["a", "b"],
        "num_sub_games": 1,
        "sub_games": [],
        "final_result": {},
        "mutual_agreement": {"sha256": "x", "confirmed": True},
    }
    validate_artifact("result", data)  # must not raise


def test_validate_artifact_lists_every_missing_required_key() -> None:
    with pytest.raises(ReportValidationError) as err:
        validate_artifact("result", {"game_id": "g"})
    message = str(err.value)
    assert "game_uid" in message
    assert "mutual_agreement" in message


def test_validate_artifact_rejects_unknown_kind() -> None:
    with pytest.raises(ReportValidationError, match="unknown artifact kind"):
        validate_artifact("receipt", {})

"""The four pure artifact builders (PRD_reporting §3; reference interface @960499fd)."""

from __future__ import annotations

from typing import Any

from report_fixtures import make_identity, make_summary

from copthief_core.domain.crypto import canonical_hash
from copthief_core.report.blocks import ended_at, group_block, hardware_spec, tokens_series
from copthief_core.report.builders import (
    build_config_artifact,
    build_declaration,
    build_log,
    build_result,
)
from copthief_core.report.consensus import consensus_signature


def test_hardware_spec_keeps_exactly_the_six_book_fields_renaming_gpu() -> None:
    spec = make_identity("team-a", 8801)["spec"]
    block = hardware_spec(spec)
    assert set(block) == {"cpu_type", "cpu_freq_mhz", "cpu_cores", "ram_gb", "gpu_model", "vram_gb"}
    assert block["gpu_model"] == spec["gpu_type"]


def test_group_block_signature_is_sign_then_insert() -> None:
    block = group_block(make_identity("team-a", 8801))
    signature = block.pop("signature")
    assert signature == consensus_signature(block)


def test_ended_at_adds_duration_and_echoes_unparsable_input() -> None:
    assert ended_at("2026-07-19T10:00:00+00:00", 90.0) == "2026-07-19T10:01:30+00:00"
    assert ended_at("not-a-time", 5.0) == "not-a-time"


def test_tokens_series_sums_per_group_over_sub_games() -> None:
    sub_games = [{"tokens": {"a": 3, "b": 1}}, {"tokens": {"a": 2}}]
    assert tokens_series(sub_games, ["a", "b"]) == {"a": 5, "b": 1}


def test_build_declaration_orders_groups_own_first() -> None:
    own, opp = make_identity("team-a", 8801), make_identity("team-b", 8802)
    declaration = build_declaration(
        game_id="team-a-vs-team-b",
        game_uid="uid-1",
        timezone="Asia/Jerusalem",
        game_started_at="2026-07-19T10:00:00+00:00",
        game_ended_at="2026-07-19T10:01:00+00:00",
        num_sub_games=2,
        max_tokens_per_game=200000,
        own=own,
        opponent=opp,
    )
    assert declaration["declaration_type"] == "pre_game_declaration"
    assert declaration["groups"]["group_1"]["group_id"] == "team-a"
    assert declaration["groups"]["group_2"]["group_id"] == "team-b"
    assert declaration["num_sub_games"] == 2
    assert declaration["links"]["declaration"] == "declaration_team-a-vs-team-b.json"


def test_build_config_artifact_locks_shared_terms_with_compact_canonical(
    shared_terms: dict[str, Any],
) -> None:
    artifact = build_config_artifact(shared_terms, "gid", "uid", 1)
    assert artifact["config_sha256"] == canonical_hash(shared_terms)
    assert artifact["config_name"] == "config_gid_g01.json"
    assert artifact["scoring"] == shared_terms["scoring"]
    assert artifact["sub_game_number"] == 1


def test_build_log_signs_records_and_mirrors_the_audit_verdict() -> None:
    summary = make_summary(role="thief", audit_passed=True)
    log = build_log(summary, "gid", "uid", "team-a", "team-b")
    assert log["summary"]["group_id"] == "team-a"
    assert log["summary"]["opponent_group_id"] == "team-b"
    assert log["summary"]["winner_role"] == summary["winner"]
    assert log["records"] == summary["records"]
    assert log["mutual_agreement"]["sha256"] == consensus_signature(summary["records"])
    assert log["mutual_agreement"]["confirmed"] is True


def test_build_result_appends_token_series_and_confirms_only_when_all_verified() -> None:
    sub_games = [
        {"sub_game_number": 1, "tokens": {"a": 0, "b": 0}, "audit": {"log_verified": True}},
        {"sub_game_number": 2, "tokens": {"a": 4, "b": 0}, "audit": {"log_verified": False}},
    ]
    aggregate = {"total_score": {"a": 20, "b": 15}, "winner_group": "a", "series_tie": False}
    result = build_result("gid", "uid", ["a", "b"], sub_games, aggregate, "sha-x")
    assert result["final_result"]["tokens_total_series"] == {"a": 4, "b": 0}
    assert result["final_result"]["winner_group"] == "a"
    assert result["num_sub_games"] == 2
    assert result["mutual_agreement"] == {"sha256": "sha-x", "confirmed": False}

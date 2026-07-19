"""Byte-level report-artifact conformance vs the reference docs/sample-run (M6-2 DoD).

Fixture provenance: SOURCE.md — the four JSONs under ``sample_run/`` are copied verbatim
(LF-rewritten) from the reference checkout @960499fd (oracle only, ADR-0002; attributed
fixtures per PRD_reporting §9 D4). Every embedded hash must recompute through OUR code
and every file must reproduce byte-for-byte from OUR serializer — the settlement rail
(consensus signature, Alon's find) is pinned here exactly like the kit CORE vectors.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from copthief_core.domain.crypto import canonical_hash
from copthief_core.report import schema_text
from copthief_core.report.consensus import consensus_signature
from copthief_core.report.emit import artifact_bytes
from copthief_core.report.schemas import SCHEMA_VERSION, validate_artifact
from copthief_core.report.scores import symmetric_outcome

FIXTURES = Path(__file__).parent / "sample_run"
GAME_ID = "segal-police-team-vs-segal-thief-team"
FILES = {
    "declaration": f"declaration_{GAME_ID}.json",
    "config": f"config_{GAME_ID}_g01.json",
    "log": f"log_{GAME_ID}_g01.json",
    "result": f"result_{GAME_ID}.json",
}
# Keys build_config_artifact ADDS around the shared terms (everything else is signed).
# Brute-force-verified vs the fixture: the reference's shared game.json carries
# `schema_version` AND `_note` UNDER the lock (the writer then overwrites the displayed
# schema_version with its own constant — they coincide at this generation).
CONFIG_ADDED = {
    "_schema",
    "game_id",
    "game_uid",
    "sub_game_number",
    "links",
    "config_name",
    "config_sha256",
}


def load(kind: str) -> dict[str, Any]:
    return json.loads((FIXTURES / FILES[kind]).read_text(encoding="utf-8"))


def test_declaration_group_signatures_recompute_sign_then_insert() -> None:
    for name, block in load("declaration")["groups"].items():
        body = {k: v for k, v in block.items() if k != "signature"}
        assert consensus_signature(body) == block["signature"], name


def test_config_sha256_recomputes_with_the_compact_kit_canonical() -> None:
    config = load("config")
    shared = {k: v for k, v in config.items() if k not in CONFIG_ADDED}
    assert canonical_hash(shared) == config["config_sha256"]


def test_log_mutual_agreement_signs_the_full_records_list() -> None:
    log = load("log")
    assert consensus_signature(log["records"]) == log["mutual_agreement"]["sha256"]


def test_result_mutual_agreement_signs_the_symmetric_outcome_only() -> None:
    result = load("result")
    aggregate = {k: v for k, v in result["final_result"].items() if k != "tokens_total_series"}
    rebuilt = symmetric_outcome(result["game_id"], aggregate, result["sub_games"])
    assert consensus_signature(rebuilt) == result["mutual_agreement"]["sha256"]


@pytest.mark.parametrize("kind", sorted(FILES))
def test_artifact_reproduces_reference_bytes(kind: str) -> None:
    """Our serializer over the parsed reference dict == the reference file bytes."""
    raw = (FIXTURES / FILES[kind]).read_bytes()
    assert artifact_bytes(json.loads(raw.decode("utf-8"))) == raw


@pytest.mark.parametrize("kind", sorted(FILES))
def test_sample_artifacts_pass_our_validation(kind: str) -> None:
    validate_artifact(kind, load(kind))


def test_schema_strings_match_the_reference_generation() -> None:
    assert load("declaration")["_schema"] == schema_text.SCHEMA_DECLARATION
    assert load("config")["_schema"] == schema_text.SCHEMA_CONFIG
    assert load("log")["_schema"] == schema_text.SCHEMA_LOG
    assert load("result")["_schema"] == schema_text.SCHEMA_RESULT
    assert load("declaration")["links"]["_remark"] == schema_text.LINKS_REMARK
    assert load("result")["schema_version"] == SCHEMA_VERSION

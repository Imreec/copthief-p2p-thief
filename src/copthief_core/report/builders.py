"""The four pure artifact builders (book App F templates; PRD_reporting §3).

Interface-mirrored from the reference @960499fd (ADR-0002): each returns a dict
matching the sample-run shapes byte-pinned in tests/conformance. No I/O — disk
wiring lives in `report/emit`. The config lock uses the COMPACT kit canonical
(`domain/crypto.canonical_hash`); every consensus-form signature is spaced
(`report/consensus`) — the two must never swap.
"""

from __future__ import annotations

from typing import Any

from copthief_core.domain.crypto import canonical_hash
from copthief_core.report.blocks import ended_at, group_block, tokens_series
from copthief_core.report.consensus import consensus_signature
from copthief_core.report.schema_text import (
    SCHEMA_CONFIG,
    SCHEMA_DECLARATION,
    SCHEMA_LOG,
    SCHEMA_RESULT,
)
from copthief_core.report.schemas import (
    DEFAULT_TIMEZONE,
    SCHEMA_VERSION,
    config_filename,
    links,
)


def build_declaration(
    *,
    game_id: str,
    game_uid: str,
    timezone: str,
    game_started_at: str,
    game_ended_at: str,
    num_sub_games: int,
    max_tokens_per_game: int,
    own: dict[str, Any],
    opponent: dict[str, Any],
) -> dict[str, Any]:
    """Template 1: the whole-series pre-game declaration (both teams' static blocks;
    group_1 = the writing peer, mirroring the reference's own ordering)."""
    return {
        "_schema": SCHEMA_DECLARATION,
        "schema_version": SCHEMA_VERSION,
        "declaration_type": "pre_game_declaration",
        "game_id": game_id,
        "game_uid": game_uid,
        "links": links(game_id),
        "timezone": timezone,
        "game_started_at": game_started_at,
        "game_ended_at": game_ended_at,
        "num_sub_games": num_sub_games,
        "max_tokens_per_game": max_tokens_per_game,
        "groups": {"group_1": group_block(own), "group_2": group_block(opponent)},
    }


def build_config_artifact(
    shared_terms: dict[str, Any], game_id: str, game_uid: str, sub_game_number: int
) -> dict[str, Any]:
    """Template 2: the agreed byte-identical terms + their compact-canonical lock."""
    artifact: dict[str, Any] = {"_schema": SCHEMA_CONFIG, **shared_terms}
    artifact.update(
        {
            "schema_version": SCHEMA_VERSION,
            "game_id": game_id,
            "game_uid": game_uid,
            "sub_game_number": sub_game_number,
            "links": links(game_id),
            "config_name": config_filename(game_id, sub_game_number),
            "config_sha256": canonical_hash(shared_terms),
        }
    )
    return artifact


def build_log(
    summary: dict[str, Any],
    game_id: str,
    game_uid: str,
    group_id: str,
    opponent_group_id: str,
) -> dict[str, Any]:
    """Template 3: one peer's per-sub-game commit-reveal log from its summary; the
    mutual block signs the FULL records list (consensus form)."""
    log_summary = {
        "sub_game_number": summary["sub_game_number"],
        "group_id": group_id,
        "role": summary["role"],
        "opponent_group_id": opponent_group_id,
        "result": summary["result"],
        "winner_role": summary["winner"],
        "steps": summary["steps"],
        "timezone": summary.get("timezone", DEFAULT_TIMEZONE),
        "started_at": summary["started_at"],
        "ended_at": ended_at(summary["started_at"], summary["duration_seconds"]),
        "duration_seconds": summary["duration_seconds"],
        "tokens_total": summary["tokens_total"],
        "audit": summary["audit"],
    }
    return {
        "_schema": SCHEMA_LOG,
        "schema_version": SCHEMA_VERSION,
        "game_id": game_id,
        "game_uid": game_uid,
        "links": links(game_id),
        "summary": log_summary,
        "records": summary["records"],
        "mutual_agreement": {
            "opponent_group_id": opponent_group_id,
            "sha256": consensus_signature(summary["records"]),
            "confirmed": summary["audit"]["passed"],
        },
    }


def build_result(
    game_id: str,
    game_uid: str,
    group_ids: list[str],
    sub_games: list[dict[str, Any]],
    aggregate_out: dict[str, Any],
    mutual_sha256: str,
    league: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Template 4: the aggregated final result; `confirmed` derives from every
    sub-game's audit (never declared — PRD FR-11). `league` = the M7-34 standings
    fields (game-count declarations, first meeting, diversity reward), appended
    AFTER the signed symmetric outcome is derived — they are per-side claims."""
    final_result = {**aggregate_out, "tokens_total_series": tokens_series(sub_games, group_ids)}
    final_result.update(league or {})
    return {
        "_schema": SCHEMA_RESULT,
        "schema_version": SCHEMA_VERSION,
        "report_type": "final_game_result",
        "game_id": game_id,
        "game_uid": game_uid,
        "links": links(game_id),
        "timezone": DEFAULT_TIMEZONE,
        "groups": list(group_ids),
        "num_sub_games": len(sub_games),
        "sub_games": sub_games,
        "final_result": final_result,
        "mutual_agreement": {
            "sha256": mutual_sha256,
            "confirmed": all(sg.get("audit", {}).get("log_verified", False) for sg in sub_games),
        },
    }

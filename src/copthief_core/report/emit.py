"""Series emission: wire the pure builders to disk (PRD_reporting §3).

One declaration + result per series, one config + log + Hebrew report per sub-game,
all named from the shared ``game_id``, written into the writer's OWN group subfolder
(roles alternate; group_id is the stable per-peer key). Byte discipline: UTF-8 LF
bytes, ``indent=2, ensure_ascii=False``, no trailing newline — pinned against the
reference sample-run. Every artifact validates BEFORE it touches disk (PLAN §7);
``emit_series`` returns the result dict, whose file bytes ARE the emailed bytes
(canonical-bytes = emailed-bytes, PLAN §4; the M6-4 sender reads the file).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from copthief_core.domain.scoring import ScoringTable
from copthief_core.report.blocks import ended_at
from copthief_core.report.builders import (
    build_config_artifact,
    build_declaration,
    build_log,
    build_result,
)
from copthief_core.report.consensus import consensus_signature
from copthief_core.report.hebrew import build_report
from copthief_core.report.schemas import (
    DEFAULT_TIMEZONE,
    config_filename,
    declaration_filename,
    log_filename,
    report_filename,
    result_filename,
    validate_artifact,
)
from copthief_core.report.scores import aggregate_groups, subgame_score, symmetric_outcome


def artifact_bytes(data: dict[str, Any]) -> bytes:
    """The artifact byte form (reference-pinned): spaced indent-2 JSON, real UTF-8."""
    return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")


def write_artifact(out_dir: Path, filename: str, data: dict[str, Any]) -> Path:
    """Write one artifact as LF bytes (never platform newlines — ops gotcha #6)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / filename
    path.write_bytes(artifact_bytes(data))
    return path


def _roles(own_gid: str, opp_gid: str, own_role: str) -> dict[str, str]:
    opp_role = "thief" if own_role == "police" else "police"
    return {own_gid: own_role, opp_gid: opp_role}


def _own_commit(summary: dict[str, Any]) -> str:
    """The commit hash our sealed step-0 recorded, or "unknown" without one.

    M7-28: the book mandates the exact commit played per sub-game in the closing
    email's JSON (ch.5 → §9.3.3); the reference's sample emits "unknown" — a
    book-vs-reference contradiction resolved toward the book. The opponent column
    is NOT ours to fill: their hash never crosses the wire today (proposed as a
    negotiate-extras declaration; their own report carries theirs).
    """
    for record in summary.get("records", []):
        payload = record.get("payload", {})
        if payload.get("type") == "system_spec":
            return str(payload.get("github_commit", "unknown"))
    return "unknown"


def subgame_entry(
    summary: dict[str, Any], game_id: str, own_gid: str, opp_gid: str, table: ScoringTable
) -> dict[str, Any]:
    """One sub-game's result row: roles, outcome, per-group score, audit verdict.

    Opponent tokens are unknowable to this peer (their own report carries them) —
    0 mirrors the reference's stance. `log_files` uses the sample's flat filenames
    (M7-28 — the M7-27 cross-team diff named our subdir prefix as the deviation).
    """
    roles = _roles(own_gid, opp_gid, summary["role"])
    n = summary["sub_game_number"]
    winner = next((g for g, r in roles.items() if r == summary["winner"]), None)
    passed = summary["audit"]["passed"]
    return {
        "sub_game_number": n,
        "roles": roles,
        "started_at": summary["started_at"],
        "ended_at": ended_at(summary["started_at"], summary["duration_seconds"]),
        "result": summary["result"],
        "winner_group": winner,
        "tie": winner is None,
        "github_commit": {own_gid: _own_commit(summary), opp_gid: "unknown"},
        "tokens": {own_gid: summary["tokens_total"], opp_gid: 0},
        "score": subgame_score(summary["result"], roles, table),
        "log_files": {
            own_gid: log_filename(game_id, n),
            opp_gid: log_filename(game_id, n),
        },
        "audit": {"log_verified": passed, "tampered": not passed},
    }


def emit_series(
    *,
    summaries: list[dict[str, Any]],
    own_identity: dict[str, Any],
    opponent_identity: dict[str, Any],
    game_id: str,
    game_uid: str,
    shared_terms: dict[str, Any],
    terms: dict[str, Any],
    table: ScoringTable,
    out_root: Path,
) -> dict[str, Any]:
    """Write all artifacts for a finished series; return the result dict.

    Input: reference-shaped per-sub-game summaries + both identities + the signed
    terms (shared_terms = game.json sections; terms = the translated rules dict the
    Hebrew report embeds). Output: the validated result artifact (also on disk).
    """
    own_gid, opp_gid = own_identity["group_id"], opponent_identity["group_id"]
    own_dir = out_root / own_gid
    first, last = summaries[0], summaries[-1]
    max_tokens = shared_terms["network_and_league"]["token_budget_per_series"]

    declaration = build_declaration(
        game_id=game_id,
        game_uid=game_uid,
        timezone=DEFAULT_TIMEZONE,
        game_started_at=first["started_at"],
        game_ended_at=ended_at(last["started_at"], last["duration_seconds"]),
        num_sub_games=len(summaries),
        max_tokens_per_game=max_tokens,
        own=own_identity,
        opponent=opponent_identity,
    )
    validate_artifact("declaration", declaration)
    write_artifact(own_dir, declaration_filename(game_id), declaration)

    sub_games = []
    for summary in summaries:
        n = summary["sub_game_number"]
        config = build_config_artifact(shared_terms, game_id, game_uid, n)
        validate_artifact("config", config)
        write_artifact(own_dir, config_filename(game_id, n), config)
        log = build_log(summary, game_id, game_uid, own_gid, opp_gid)
        validate_artifact("log", log)
        write_artifact(own_dir, log_filename(game_id, n), log)
        write_artifact(own_dir, report_filename(game_id, n), build_report(summary, terms))
        sub_games.append(subgame_entry(summary, game_id, own_gid, opp_gid, table))

    aggregate = aggregate_groups(sub_games, table.tie_score)
    mutual = consensus_signature(symmetric_outcome(game_id, aggregate, sub_games))
    result = build_result(
        game_id, game_uid, sorted([own_gid, opp_gid]), sub_games, aggregate, mutual
    )
    validate_artifact("result", result)
    write_artifact(own_dir, result_filename(game_id), result)
    return result

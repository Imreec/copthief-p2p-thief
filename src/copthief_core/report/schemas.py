"""Artifact naming grammar + pre-write validation (PRD_reporting §3; book App F).

Filenames derive from ``game_id`` so files from different games never mix (the
reference's own links `_remark` states the rule); per-sub-game files zero-pad the
sub-game number (``_g<NN>``). Validation is required-keys-only on purpose: unknown
keys are tolerated (forward-compat, same stance as the wire layer).
"""

from __future__ import annotations

from typing import Any

from copthief_core.report.schema_text import LINKS_REMARK

SCHEMA_VERSION = "1.1"
DEFAULT_TIMEZONE = "Asia/Jerusalem"


class ReportValidationError(Exception):
    """An artifact is malformed: unknown kind or missing required keys."""


def declaration_filename(game_id: str) -> str:
    """`declaration_<game_id>.json` (whole-series file)."""
    return f"declaration_{game_id}.json"


def config_filename(game_id: str, sub_game_number: int) -> str:
    """`config_<game_id>_g<NN>.json` (per-sub-game, zero-padded)."""
    return f"config_{game_id}_g{sub_game_number:02d}.json"


def log_filename(game_id: str, sub_game_number: int) -> str:
    """`log_<game_id>_g<NN>.json` (per-sub-game, zero-padded)."""
    return f"log_{game_id}_g{sub_game_number:02d}.json"


def report_filename(game_id: str, sub_game_number: int) -> str:
    """`report_<game_id>_g<NN>.json` — the per-sub-game Hebrew report (PRD D2:
    written beside the four reference artifacts; not part of the reference set)."""
    return f"report_{game_id}_g{sub_game_number:02d}.json"


def result_filename(game_id: str) -> str:
    """`result_<game_id>.json` (whole-series file)."""
    return f"result_{game_id}.json"


def links(game_id: str) -> dict[str, str]:
    """The shared links block: logical role -> filename; per-sub-game entries keep
    the literal ``g<NN>`` placeholder because <NN> varies per file."""
    return {
        "_remark": LINKS_REMARK,
        "declaration": declaration_filename(game_id),
        "config": f"config_{game_id}_g<NN>.json",
        "log": f"log_{game_id}_g<NN>.json",
        "result": result_filename(game_id),
    }


_COMMON = frozenset({"_schema", "schema_version", "game_id", "game_uid", "links"})
REQUIRED_KEYS: dict[str, frozenset[str]] = {
    "declaration": _COMMON
    | frozenset(
        {
            "declaration_type",
            "timezone",
            "game_started_at",
            "game_ended_at",
            "num_sub_games",
            "max_tokens_per_game",
            "groups",
        }
    ),
    "config": _COMMON | frozenset({"sub_game_number", "config_name", "config_sha256"}),
    "log": _COMMON | frozenset({"summary", "records", "mutual_agreement"}),
    "result": _COMMON
    | frozenset(
        {
            "report_type",
            "timezone",
            "groups",
            "num_sub_games",
            "sub_games",
            "final_result",
            "mutual_agreement",
        }
    ),
}


def validate_artifact(kind: str, data: dict[str, Any]) -> None:
    """Refuse a malformed artifact BEFORE it is written or sent (PLAN §7).

    Input: artifact kind + candidate dict. Raises ReportValidationError naming the
    kind and EVERY missing required key; unknown keys pass (forward-compat).
    """
    required = REQUIRED_KEYS.get(kind)
    if required is None:
        raise ReportValidationError(f"unknown artifact kind: {kind!r}")
    missing = sorted(required - data.keys())
    if missing:
        raise ReportValidationError(f"{kind} artifact missing required keys: {', '.join(missing)}")

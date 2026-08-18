"""Assemble a whole-series artifact from committed sub-game logs (M7-4).

`sdk/series_run` emits a series from live in-process summaries, which fits self-play but
not a live tunnel series: under the rolling-window protocol each sub-game is its own
process, so aggregation happens after every session has exited.

This module closes that gap by joining `summary_from_log` to `report/emit.emit_series`.
The scoring table does the arithmetic and the step-0 declarations ride along, so the
emitted artifact is the same shape a counted series produces — the difference is only
where the summaries came from (archived evidence rather than live memory).

One sub-game that never settled refuses the WHOLE series: a report that quietly drops a
game is precisely the contradictory report App E rule 35 punishes on both teams.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from copthief_core.domain.crypto import series_game_id
from copthief_core.domain.terms import terms_from_config
from copthief_core.report.emit import emit_series
from copthief_core.report.summary_from_log import summary_from_log
from copthief_core.sdk.identity import identity_block
from copthief_core.shared.config_model import Constitution, PrivateSettings

__all__ = ["opponent_identity_from_logs", "series_artifact_from_logs"]


def series_artifact_from_logs(
    *,
    logs: list[Path],
    constitution: Constitution,
    private: PrivateSettings,
    config_dir: Path,
    opponent_group: str,
    out_root: Path,
    opponent_identity: dict[str, Any] | None = None,
    durations: dict[int, float] | None = None,
    counted: bool = False,
) -> dict[str, Any]:
    """Write the whole-series artifact set from `logs` in sub-game order (Input: one
    settled log per sub-game + the signed constitution + our private identity + how long
    each sub-game took where the caller measured it; Output: the result dict; Raises:
    SummaryRebuildError if any sub-game never settled).

    `game_uid` is taken from the sub-games themselves — it is derived from the terms and
    both group ids, so every sub-game of one pairing shares it by construction.

    `durations` is what turns each sub-game's `ended_at` into a real end time; a caller
    that never measured (rebuilding from archived logs long afterwards) leaves it out and
    the entry says the game ended when it started, which is visibly a non-claim rather
    than an invented one.
    """
    measured = durations or {}
    summaries = [
        summary_from_log(
            path,
            sub_game_number=n,
            group_name=private.group_name,
            duration_seconds=measured.get(n, 0.0),
        )
        for n, path in enumerate(logs, start=1)
    ]
    shared_terms = json.loads((config_dir / "game.json").read_text(encoding="utf-8"))
    return emit_series(
        summaries=summaries,
        own_identity=identity_block(private),
        opponent_identity=opponent_identity or opponent_identity_from_logs(logs, opponent_group),
        game_id=series_game_id(private.group_id, opponent_group),
        game_uid=_game_uid(logs),
        shared_terms=shared_terms,
        terms=terms_from_config(constitution),
        table=constitution.scoring,
        out_root=out_root,
        counted=counted,
        # M7-34: one counted game per pair (book §9.2.1), so the ledger of counted
        # opponents decides the first-meeting flag; the default empty ledger reads
        # "no counted game against anyone yet" — true until Imree records one.
        first_meeting=opponent_group not in private.counted_opponents,
    )


def opponent_identity_from_logs(logs: list[Path], opponent_group: str) -> dict[str, Any]:
    """The opponent's declared identity, normalised to the seven keys the declaration
    block needs (Input: the sub-game logs + their negotiated group id; Output: the block).

    Read from the archived `agreement_received` — their own words, not ours. Keys they
    did not declare come back EMPTY rather than filled in: a declaration block is a
    record of what a team stated about itself, and inventing a plausible value there
    would be a fabricated record in a signed artifact. An interop note worth keeping:
    the reference's F8b block carries all seven, but a conforming peer may send fewer.

    Only an identity that AGREES with the pairing is adopted. The wire guard refuses
    a wrong-opponent agreement, but its reception is still logged — and on 2026-08-18
    a third team's single refused push sat first in the log and renamed all six rows
    of the mailed artifact. The configured pairing names the series; a stranger's
    record never does, however early it arrived.
    """
    declared: dict[str, Any] = {}
    group_id = opponent_group
    for path in logs:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("event") != "agreement_received":
                continue
            raw = event.get("raw", {})
            candidate = dict(raw.get("identity") or {})
            candidate_gid = str(candidate.get("group_id") or raw.get("group_id") or "")
            if candidate_gid and candidate_gid != opponent_group:
                continue
            declared = candidate
            break
        if declared:
            break
    count = declared.get("counted_games_played")
    return {
        "group_id": group_id,
        "group_name": str(declared.get("group_name", "")),
        "members": list(declared.get("members", [])),
        "repos": dict(declared.get("repos", {})),
        "mcp_servers": dict(declared.get("mcp_servers", {})),
        "llm_model": str(declared.get("llm_model", "")),
        "spec": _spec_from(declared),
        # M7-34: their game-count declaration; None when they declared none (never
        # invented — the league fields fall back to 0-played, the honest floor).
        "counted_games_played": int(count) if count is not None else None,
    }


def _spec_from(declared: dict[str, Any]) -> dict[str, Any]:
    """The hardware spec under EITHER wire spelling (M7-38 — the 16:00 nulls).

    Ours ships `spec` (reference F8b, sysinfo key names); the opponent team ships
    `hardware_spec` (the book-attached declaration shape, `gpu_model`). Accept both,
    remapped to the sysinfo names downstream expects — their real values must reach
    our declaration, and absence stays empty rather than invented.
    """
    if declared.get("spec"):
        return dict(declared["spec"])
    declaration_shaped = declared.get("hardware_spec")
    if not isinstance(declaration_shaped, dict):
        return {}
    remapped = dict(declaration_shaped)
    if "gpu_model" in remapped:
        remapped["gpu_type"] = remapped.pop("gpu_model")
    return remapped


def _game_uid(logs: list[Path]) -> str:
    """The `game_uid` the sub-games negotiated ("" if no log carries one)."""
    for path in logs:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("event") == "negotiated" and event.get("game_uid"):
                return str(event["game_uid"])
    return ""

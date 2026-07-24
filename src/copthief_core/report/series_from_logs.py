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
        game_id=f"{private.group_id}-vs-{opponent_group}",
        game_uid=_game_uid(logs),
        shared_terms=shared_terms,
        terms=terms_from_config(constitution),
        table=constitution.scoring,
        out_root=out_root,
    )


def opponent_identity_from_logs(logs: list[Path], opponent_group: str) -> dict[str, Any]:
    """The opponent's declared identity, normalised to the seven keys the declaration
    block needs (Input: the sub-game logs + their negotiated group id; Output: the block).

    Read from the archived `agreement_received` — their own words, not ours. Keys they
    did not declare come back EMPTY rather than filled in: a declaration block is a
    record of what a team stated about itself, and inventing a plausible value there
    would be a fabricated record in a signed artifact. An interop note worth keeping:
    the reference's F8b block carries all seven, but a conforming peer may send fewer.
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
            declared = dict(raw.get("identity") or {})
            group_id = str(declared.get("group_id") or raw.get("group_id") or opponent_group)
            break
        if declared:
            break
    return {
        "group_id": group_id,
        "group_name": str(declared.get("group_name", "")),
        "members": list(declared.get("members", [])),
        "repos": dict(declared.get("repos", {})),
        "mcp_servers": dict(declared.get("mcp_servers", {})),
        "llm_model": str(declared.get("llm_model", "")),
        "spec": dict(declared.get("spec", {})),
    }


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

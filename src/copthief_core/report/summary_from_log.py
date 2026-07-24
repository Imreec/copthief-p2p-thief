"""Rebuild a reference-shaped sub-game summary from a committed game log (M7-4).

`peer/summary_build.build_summary` reads a live `PeerSession`, which is the right source
while a game is in flight. A live tunnel series, though, plays each sub-game in its own
process (the rolling window protocol), so by aggregation time every session is gone.

The log holds the same truth in archived form: our sealed records ride the `audit` event
(step-0 declaration first, per M6-3), the opponent's turns ride `turn_received` verbatim,
and the settlement verdict rides `peer_result`. Deriving the series artifact from the log
is therefore not a workaround but a stronger guarantee — **what we report is exactly what
we archived**, and a third party can re-derive it from the same committed bytes.

Refuses loudly on a log that never reached settlement: an aborted game has no revealed
records and therefore no honest summary, and a hollow entry must never reach an artifact.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

__all__ = ["SummaryRebuildError", "summary_from_log"]

_WINNERS = {"capture": "police", "survival": "thief"}


class SummaryRebuildError(RuntimeError):
    """The log cannot yield an honest summary (no audit, or no settled result)."""


def _events(log_path: Path) -> list[dict[str, Any]]:
    # A sub-game whose process died before writing anything is the emptiest case of "no
    # honest summary", not a different kind of problem: it refuses through the same door
    # so an operator sees the named refusal the design promises, never a traceback.
    if not log_path.is_file():
        raise SummaryRebuildError(f"{log_path.name}: no log — the game left no record at all")
    text = log_path.read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _last(events: list[dict[str, Any]], kind: str) -> dict[str, Any] | None:
    found = [e for e in events if e.get("event") == kind]
    return found[-1] if found else None


def summary_from_log(
    log_path: Path,
    *,
    sub_game_number: int,
    group_name: str,
    duration_seconds: float = 0.0,
    tokens_total: int = 0,
) -> dict[str, Any]:
    """One reference-shaped summary rebuilt from a finished game's log (Input: the JSONL
    path + the series bookkeeping the log does not carry; Output: the dict the `report/`
    builders consume; Raises: SummaryRebuildError if the game never settled)."""
    events = _events(log_path)
    audit = _last(events, "audit")
    if audit is None:
        raise SummaryRebuildError(f"{log_path.name}: no audit event — the game never settled")
    result_event = _last(events, "peer_result")
    if result_event is None:
        raise SummaryRebuildError(f"{log_path.name}: no peer_result event — no settled result")

    payload = audit.get("payload", {})
    records = list(payload.get("records", []))
    settled = result_event.get("payload", {})
    claim = str(payload.get("result_claim", ""))
    # Step math counts GAME records only: the sealed step-0 declaration leads the audit
    # but is not a step (M6-3 — the live summary applies the identical rule).
    game_records = [r for r in records if int(r.get("payload", {}).get("step", 0)) >= 1]
    history = [e.get("raw", {}) for e in events if e.get("event") == "turn_received"]

    return {
        "sub_game_number": sub_game_number,
        "role": str(payload.get("sender", "")),
        "result": claim,
        "winner": _WINNERS.get(claim),
        "steps": len(game_records),
        "group_name": group_name,
        "started_at": _started_at(events),
        "duration_seconds": duration_seconds,
        "tokens_total": tokens_total,
        "audit": {
            "passed": bool(settled.get("audit_ok")),
            "verified_steps": len(history) if settled.get("audit_ok") else 0,
            "failed_steps": [],
        },
        "records": records,
        "history": history,
    }


def _started_at(events: list[dict[str, Any]]) -> str:
    """The first outbound turn's sealed ISO timestamp ("" when the log has none).

    Taken from the sealed message rather than a fresh clock read: the summary must
    describe the archived game, never the moment it was rebuilt.
    """
    for event in events:
        if event.get("event") == "turn":
            stamp = event.get("message", {}).get("timestamp")
            if isinstance(stamp, str):
                return stamp
    return ""

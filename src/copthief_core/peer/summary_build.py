"""M6-6: PeerSession + PeerGameResult -> the reference-shaped sub-game summary.

The summary is the contract between the peer layer and the report builders
(PRD_reporting §3/§6): wire result vocabulary, the sealed step-0 declaration
leading the records, the verbatim inbound history, and an audit block describing
OUR verification of the OPPONENT's audit. `failed_steps` carries our problem
strings (richer than the reference's bare step list — self-side artifact, honest
detail; disclosed in the module contract).
"""

from __future__ import annotations

from typing import Any

from copthief_core.peer.audit_flow import wire_result
from copthief_core.peer.session import PeerSession
from copthief_core.peer.settlement import PeerGameResult

_WINNERS = {"capture": "police", "survival": "thief"}


def build_summary(
    session: PeerSession,
    result: PeerGameResult,
    *,
    sub_game_number: int,
    started_at: str,
    duration_seconds: float,
) -> dict[str, Any]:
    """One reference-shaped summary (Input: the finished session + its settlement
    result + series bookkeeping; Output: the dict `report/` builders consume)."""
    wire = wire_result(result.outcome)
    spec_records = [session.spec_record] if session.spec_record is not None else []
    return {
        "sub_game_number": sub_game_number,
        "role": session.role,
        "result": wire,
        "winner": _WINNERS.get(wire),
        "steps": len(session.records),
        "group_name": session.private.group_name,
        "started_at": started_at,
        "duration_seconds": duration_seconds,
        "tokens_total": session.tokens_total,
        "audit": {
            "passed": result.audit_ok,
            "verified_steps": result.opponent_records if result.audit_ok else 0,
            "failed_steps": list(result.problems),
        },
        "records": [
            {"payload": r.payload, "nonce": r.nonce, "commit": r.commit}
            for r in spec_records + session.records
        ],
        "history": [message.to_wire() for message in session.inbound],
    }

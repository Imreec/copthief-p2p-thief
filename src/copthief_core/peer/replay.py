"""Replay-from-log (M1-8 DoD): re-verify a whole mini-game from its JSONL log alone.

Pairs each in-game TurnMessage with the audit's revealed record for the same sender and
step, then re-derives every hash: the commit that traveled must equal the sealed record's
commit, the record must re-hash cleanly, and the revealed hint must equal the hint that
actually traveled. This is the trust core the M4 replay VIEWER will render.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from copthief_core.domain.crypto import verify
from copthief_core.shared.jsonl_logger import read_events


@dataclass(frozen=True)
class ReplaySummary:
    """The re-derived truth of one logged mini-game."""

    verified: bool
    problems: list[str]
    steps: int
    outcome: str
    game_uid: str
    moves: dict[str, list[str]]


def _audit_records(events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Revealed records per sender: the initiator's audit + the responder's audit answer."""
    records: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        if event["event"] == "audit":
            records[event["payload"]["sender"]] = event["payload"]["records"]
        elif event["event"] == "audit_answer":
            answer = event["payload"]["audit"]
            records[answer["sender"]] = answer["records"]
    return records


def _check_turn(turn: dict[str, Any], revealed: list[dict[str, Any]]) -> str | None:
    """One traveled TurnMessage against its revealed record; None when consistent."""
    sender, step = turn["sender"], turn["message"]["step"]
    record = next((r for r in revealed if r["payload"].get("step") == step), None)
    if record is None:
        return f"{sender} step {step}: no revealed record in the audit"
    if record["commit"] != turn["message"]["commit"]:
        return f"{sender} step {step}: revealed commit differs from the commit that traveled"
    if not verify(record["payload"], record["nonce"], record["commit"]):
        return f"{sender} step {step}: record does not re-hash to its commit (tamper)"
    if record["payload"].get("hint") != turn["message"]["hint"]:
        return f"{sender} step {step}: revealed hint differs from the hint that traveled"
    return None


def replay_from_log(path: Path) -> ReplaySummary:
    """Re-verify a logged mini-game (Input: JSONL path; Output: ReplaySummary)."""
    events = read_events(path)
    revealed = _audit_records(events)
    turns = [e for e in events if e["event"] == "turn"]
    problems = [
        p for p in (_check_turn(t, revealed.get(t["sender"], [])) for t in turns) if p is not None
    ]
    result: dict[str, Any] = next((e["payload"] for e in events if e["event"] == "result"), {})
    moves = {
        sender: [str(r["payload"].get("move")) for r in records]
        for sender, records in revealed.items()
    }
    return ReplaySummary(
        verified=not problems,
        problems=problems,
        steps=int(result.get("steps", 0)),
        outcome=str(result.get("outcome", "unknown")),
        game_uid=str(result.get("game_uid", "")),
        moves=moves,
    )

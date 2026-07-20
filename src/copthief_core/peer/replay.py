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

# Book §7.4 exact banner strings — binary, no almost-match (App E rule 19).
VERDICT_OK = "Verified OK"
VERDICT_TAMPERED = "TAMPERED"


# The result event is named per log shape: `result` is the local two-sided match
# (peer/match), `peer_result` is a live peer's own settlement (peer/settlement). Reading
# only the former blanked the banner on EVERY live game — M7-7(4). Order is PRECEDENCE,
# not preference: a local log carries BOTH, and each side's `peer_result` counts only
# its OWN steps, so the two-sided event must win wherever it exists.
RESULT_EVENTS = ("result", "peer_result")


@dataclass(frozen=True)
class ReplaySummary:
    """The re-derived truth of one logged mini-game."""

    verified: bool
    problems: list[str]
    steps: int
    outcome: str
    game_uid: str
    moves: dict[str, list[str]]
    records_verified: int


def verdict_for(summary: ReplaySummary) -> str:
    """The viewer banner for a summary (Input: a replay summary; Output: the book's
    exact string — green `Verified OK` iff zero problems, else red `TAMPERED`)."""
    return VERDICT_OK if summary.verified else VERDICT_TAMPERED


def revealed_records(events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Revealed records per sender: our audit, the responder's answer, and (schema
    v1.1) the opponent's audit archived verbatim at `audit_received`."""
    records: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        if event["event"] == "audit":
            records[event["payload"]["sender"]] = event["payload"]["records"]
        elif event["event"] == "audit_answer":
            answer = event["payload"]["audit"]
            records[answer["sender"]] = answer["records"]
        elif event["event"] == "audit_received":
            raw = event["raw"]
            if isinstance(raw, dict) and isinstance(raw.get("records"), list):
                records.setdefault(str(raw.get("sender")), raw["records"])
    return records


def wire_turns(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every TurnMessage that traveled, as `{sender, message}` pairs: our outbound
    `turn` events plus (schema v1.1) `turn_received` archives — so a one-sided live
    log walks BOTH sides. Deduped by (sender, step); malformed archives are skipped
    (they are pre-validation dispute evidence, not verifiable protocol claims)."""
    turns = [dict(e) for e in events if e["event"] == "turn"]
    seen = {(t["sender"], t["message"].get("step")) for t in turns}
    for event in events:
        if event["event"] != "turn_received":
            continue
        raw = event.get("raw")
        if not isinstance(raw, dict):
            continue
        sender, step = raw.get("sender"), raw.get("step")
        well_formed = (
            isinstance(sender, str) and isinstance(step, int) and isinstance(raw.get("commit"), str)
        )
        if well_formed and (sender, step) not in seen:
            seen.add((sender, step))
            turns.append({"sender": sender, "message": raw})
    return turns


def result_payload(events: list[dict[str, Any]]) -> dict[str, Any]:
    """The authoritative result payload of a log (Input: the events; Output: the payload,
    or {} when the game never settled). RESULT_EVENTS order is precedence: a local log
    holds the two-sided `result` AND both sides' `peer_result`, and the latter counts
    only its own side's steps."""
    for name in RESULT_EVENTS:
        payload = next((e["payload"] for e in events if e["event"] == name), None)
        if payload is not None:
            return dict(payload)
    return {}


def negotiated_uid(events: list[dict[str, Any]]) -> str:
    """The game_uid a live log carries (Input: the events; Output: the uid, or "").

    A live `peer_result` payload has no uid: it is derived from the signed terms at the
    handshake and logged there, so `negotiated` is where a one-sided log records it.
    """
    return next((str(e.get("game_uid", "")) for e in events if e["event"] == "negotiated"), "")


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


def _check_unpaired(sender: str, records: list[dict[str, Any]]) -> list[str]:
    """Re-hash EVERY revealed record, paired or not (rule 19; M6-3): audit-only
    records — the sealed step-0 declaration above all — must not escape the iron
    rule just because no TurnMessage traveled for them."""
    problems = []
    for record in records:
        try:
            ok = verify(record["payload"], record["nonce"], record["commit"])
        except (KeyError, TypeError):
            ok = False
        if not ok:
            step = record.get("payload", {}).get("step") if isinstance(record, dict) else None
            problems.append(f"{sender} step {step}: revealed record does not re-hash (tamper)")
    return problems


def replay_from_log(path: Path) -> ReplaySummary:
    """Re-verify a logged mini-game (Input: JSONL path; Output: ReplaySummary)."""
    events = read_events(path)
    revealed = revealed_records(events)
    turns = wire_turns(events)
    problems = [
        p for p in (_check_turn(t, revealed.get(t["sender"], [])) for t in turns) if p is not None
    ]
    for sender, records in revealed.items():
        problems.extend(_check_unpaired(sender, records))
    result = result_payload(events)
    # Game turns only (step >= 1): the M6-3 step-0 declaration seals no move.
    moves = {
        sender: [
            str(r["payload"].get("move"))
            for r in records
            if isinstance(r.get("payload"), dict)
            and isinstance(r["payload"].get("step"), int)
            and r["payload"]["step"] >= 1
        ]
        for sender, records in revealed.items()
    }
    checked = sum(len(records) for records in revealed.values())
    return ReplaySummary(
        # A verdict must never be vacuously green: `not problems` is TRUE over an empty
        # log, so a truncated file used to print the book's "Verified OK" while having
        # verified nothing at all. Fail-closed, like every other rule-19 surface.
        verified=not problems and checked >= 1,
        problems=problems,
        steps=int(result.get("steps", 0)),
        outcome=str(result.get("outcome", "unknown")),
        # A live result payload carries no game_uid — it is settled at the handshake.
        game_uid=str(result.get("game_uid") or negotiated_uid(events)),
        moves=moves,
        records_verified=checked,
    )

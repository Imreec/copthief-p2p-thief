"""End-of-game audit (book ch.5 §5.4; PLAN §4): build, verify, map — never trust.

Verification re-hashes every revealed record with OUR serializer (kit §3): a single
mismatched bit proves tampering and voids the mini-game for both sides. The result is
DERIVED from protocol events and cross-checked against the revealed records
(peer/p2p.validate_opponent_audit), never taken from a claim alone.
"""

from __future__ import annotations

from typing import Any

from copthief_core.domain.crypto import verify
from copthief_core.peer.sealing import SealedTurn
from copthief_core.wire.audit import AuditPayload

# Internal outcome -> the reference's wire result vocabulary (spike notes §2 F5).
_WIRE_RESULTS = {"thief_survival": "survival", "cop_capture": "capture"}


def wire_result(result: str) -> str:
    """The result string as the reference speaks it on the wire ("survival", ...)."""
    return _WIRE_RESULTS.get(result, result)


def build_audit(sender: str, records: list[SealedTurn], result_claim: str) -> dict[str, Any]:
    """The outbound AuditPayload wire dict: full sealed records + withheld nonces revealed."""
    return AuditPayload.from_wire(
        {
            "sender": sender,
            "records": [
                {"payload": r.payload, "nonce": r.nonce, "commit": r.commit} for r in records
            ],
            "result_claim": result_claim,
        }
    ).to_wire()


def verify_audit(audit: AuditPayload) -> list[str]:
    """Every problem found in an opponent's audit; empty list == Verified OK.

    Checks: each record re-hashes to its commit (our serializer, kit §3), and the
    revealed GAME steps run 1..N with no gaps. Records with step < 1 (the reference
    seals a step-0 system_spec declaration — observed in the M2 smoke) are re-hashed
    but excluded from continuity. The scent-physics extension joins at M3+ (PRD FR-11).
    """
    problems: list[str] = []
    game_steps: list[int] = []
    for record in audit.records:
        step = record.payload.get("step")
        if isinstance(step, int) and step >= 1:
            game_steps.append(step)
        elif not isinstance(step, int):
            game_steps.append(-1)  # malformed step still breaks continuity below
        if not verify(record.payload, record.nonce, record.commit):
            problems.append(f"tamper: step {step} recompute does not match the sealed commit")
    expected = list(range(1, len(game_steps) + 1))
    if game_steps != expected:
        problems.append(f"continuity: revealed game steps {game_steps} != expected {expected}")
    return problems

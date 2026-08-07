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

# Sealed record `type` values that are NOT moves in the game chain (M7-42). Public so a
# peer implementation can see exactly which spellings we excuse: `system_spec` is the
# reference's step-0 declaration (we emit that spelling, the book prints `step_zero`,
# and readers accept both), `control` is a sealed control message, and `equivocation` is
# uoh-sqak's sealed evidence of a peer sending two commits for one step.
#
# Deliberately a CLOSED set: an unknown type keeps counting as a game step, so this can
# never be used to empty the continuity check. That safe default has a cost uoh-sqak
# named (2026-08-06): the list can only ever hold types that existed when it was written,
# and they had shipped `equivocation` — carrying a POSITIVE step — hours before we wrote
# it. It would have broken this very check the first time either side equivocated.
# They now stamp every non-move record with a DESCENDING NEGATIVE step, so any
# `step >= 1` filter excuses them with no agreement about type names at all; that is the
# durable fix and it is theirs. This list stays as the belt to their braces, because the
# next league team will not have made that change.
NON_GAME_RECORD_TYPES = frozenset({"system_spec", "step_zero", "control", "equivocation"})


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
    revealed GAME steps run 1..N with no gaps. Non-game records are re-hashed but
    excluded from continuity: the reference seals a step-0 `system_spec` declaration
    (observed in the M2 smoke), and a peer may seal control messages too.

    Identifying those by step NUMBER was the M7-42 defect: it assumed a non-game record
    is always numbered 0. uoh-sqak seals `control` records inside the GAME step space
    (friendly g01, 2026-08-06), so their revealed steps read [1, 2, 1, 2, 3, … 35] and
    every audit failed — two honest peers, one refused settlement. Records are
    self-describing, so ask what a record IS. Only KNOWN non-game types are excused:
    an unrecognised type still counts, so a peer cannot empty this check by inventing
    one. The scent-physics extension joins at M3+ (PRD FR-11).
    """
    problems: list[str] = []
    game_steps: list[int] = []
    for record in audit.records:
        step = record.payload.get("step")
        if record.payload.get("type") in NON_GAME_RECORD_TYPES:
            pass  # sealed and tamper-checked below, but not a move in the game chain
        elif isinstance(step, int) and step >= 1:
            game_steps.append(step)
        elif not isinstance(step, int):
            game_steps.append(-1)  # malformed step still breaks continuity below
        if not verify(record.payload, record.nonce, record.commit):
            problems.append(f"tamper: step {step} recompute does not match the sealed commit")
    expected = list(range(1, len(game_steps) + 1))
    # Terminal-message convention (M5 friendly g2 live finding): a caught reference
    # thief seals its mandatory final message at its CURRENT step, so its revealed
    # steps run [1..N, N]. Exactly one TRAILING repeat is legal; anything else breaks.
    trailing_repeat = (
        len(game_steps) >= 2
        and game_steps[-1] == game_steps[-2]
        and game_steps[:-1] == list(range(1, len(game_steps)))
    )
    if game_steps != expected and not trailing_repeat:
        problems.append(f"continuity: revealed game steps {game_steps} != expected {expected}")
    return problems

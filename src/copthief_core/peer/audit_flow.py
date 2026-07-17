"""End-of-game audit (book ch.5 §5.4; PLAN §4): build, verify, derive — never trust.

Verification re-hashes every revealed record with OUR serializer (kit §3): a single
mismatched bit proves tampering and voids the mini-game for both sides. The result is
DERIVED from the verified records, never taken from a claim (PRD "capture/score is
derived, never declared").
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from copthief_core.domain.crypto import verify
from copthief_core.domain.state_machine import GameState
from copthief_core.peer.sealing import SealedTurn
from copthief_core.wire.audit import AuditPayload
from copthief_core.wire.validation import WireValidationError

if TYPE_CHECKING:  # annotation-only: session imports nothing from this module's runtime
    from copthief_core.peer.session import PeerSession


def build_audit(
    sender: str, records: list[SealedTurn], result_claim: dict[str, Any]
) -> dict[str, Any]:
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
    revealed steps run 1..N with no gaps (order/replay resistance lives inside the
    signed payloads, kit §3). The scent-physics extension joins at M3+ (PRD FR-11).
    """
    problems: list[str] = []
    steps: list[int] = []
    for record in audit.records:
        step = record.payload.get("step")
        steps.append(step if isinstance(step, int) else -1)
        if not verify(record.payload, record.nonce, record.commit):
            problems.append(f"tamper: step {step} recompute does not match the sealed commit")
    expected = list(range(1, len(steps) + 1))
    if steps != expected:
        problems.append(f"continuity: revealed steps {steps} != expected {expected}")
    return problems


def handle_submit_audit(session: PeerSession, raw: dict[str, Any]) -> dict[str, Any]:
    """The `submit_audit` tool: verify THEIR audit, answer with OURS (one round trip).

    For the last mover the audit's arrival is also the game-end acknowledgement
    (AWAITING_REVEAL → VERIFYING → GAME_OVER); any other non-terminal state means the
    protocol broke and the session collapses.
    """
    try:
        audit = AuditPayload.from_wire(raw)  # validate BEFORE any state change (FR-2)
    except WireValidationError as error:
        raise session.collapse(str(error)) from error
    if not session.machine.is_terminal:
        if session.machine.state is not GameState.AWAITING_REVEAL:
            raise session.collapse(f"audit arrived in state {session.machine.state.name}")
        session.machine.advance(GameState.VERIFYING)
        session.machine.advance(GameState.GAME_OVER)
    problems = verify_audit(audit)
    movement = session.constitution.movement
    own = build_audit(
        session.role,
        session.records,
        {
            "result": derive_result(
                steps_survived=len(session.records),
                survival_threshold=movement.survival_threshold,
                max_moves=movement.max_moves,
            ),
            "steps": len(session.records),
        },
    )
    return {
        "status": "verified" if not problems else "tamper_detected",
        "problems": problems,
        "audit": own,
    }


def derive_result(*, steps_survived: int, survival_threshold: int, max_moves: int) -> str:
    """The M1 skeleton's derived outcome: survival at the threshold/cap, else incomplete.

    Capture outcomes need the claim flow (SQ2) and belief (M3) — a skeleton mini-game
    legitimately ends by survival (PRD_engine E-4.4/E-4.5).
    """
    if steps_survived >= survival_threshold or steps_survived >= max_moves:
        return "thief_survival"
    return "incomplete"

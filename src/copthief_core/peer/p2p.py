"""Symmetric peer loop (M2 F1/F2): the reference's runtime shape, one loop for both roles.

No initiator exists: each peer pushes to the opponent and drains its own inboxes
(`PeerTransport`). The thief takes the first game turn; every later turn is a response to
an inbound one; audits are exchanged as pushes and verified locally. The loop is
transport-blind (queue pair in CI, FastMCP over tunnels live — PLAN §12).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from copthief_core.domain.state_machine import GameState
from copthief_core.peer.audit_flow import build_audit, verify_audit, wire_result
from copthief_core.peer.session import NegotiationError, PeerSession
from copthief_core.peer.transport import PeerTransport
from copthief_core.wire.audit import AuditPayload
from copthief_core.wire.validation import WireValidationError

LogFn = Callable[[dict[str, Any]], None]


@dataclass(frozen=True)
class PeerGameResult:
    """What ONE peer can honestly report about its finished mini-game."""

    role: str
    outcome: str
    steps: int
    game_uid: str
    audit_ok: bool
    opponent_claim: str
    problems: tuple[str, ...]


def validate_opponent_audit(
    raw: dict[str, Any], *, survival_threshold: int
) -> tuple[str, list[str]]:
    """(their result claim, every problem found) — empty problems == Verified OK.

    Beyond the re-hash + continuity check, the derived-never-declared backstop: a
    "survival" claim must be backed by revealed game steps reaching the threshold.
    """
    try:
        audit = AuditPayload.from_wire(raw)
    except WireValidationError as error:
        return ("invalid", [str(error)])
    problems = verify_audit(audit)
    game_steps = [
        r.payload["step"]
        for r in audit.records
        if isinstance(r.payload.get("step"), int) and r.payload["step"] >= 1
    ]
    # Survival is the THIEF's outcome: only the thief's own audit must show the
    # surviving step count (the police ends one turn short on the inbound win claim).
    if (
        audit.result_claim == "survival"
        and audit.sender == "thief"
        and len(game_steps) < survival_threshold
    ):
        problems.append(
            f"claim 'survival' with {len(game_steps)} revealed steps "
            f"below the threshold {survival_threshold}"
        )
    return (audit.result_claim, problems)


def _send_own_turn(session: PeerSession, transport: PeerTransport, emit: LogFn) -> None:
    """Take, log and push one of our turns (the turn token travels with it)."""
    message = session.take_turn(now=time.time())
    emit({"event": "turn", "sender": session.role, "message": message})
    transport.send_turn(message)


def run_peer_game(
    session: PeerSession,
    transport: PeerTransport,
    *,
    turn_timeout: float,
    poll_interval: float,
    log: LogFn | None = None,
) -> PeerGameResult:
    """Play ONE mini-game as `session`'s role over `transport` (Input: a fresh session +
    a connected transport + the private timing budget; Output: this side's result).

    Raises NegotiationError if the handshake never completes; a protocol-violating
    inbound turn propagates after collapsing the session (PLAN §5).
    """
    emit = log or (lambda event: None)
    theirs = transport.exchange_agreement(session.negotiate_payload())
    if theirs is None:
        raise NegotiationError("opponent never sent its agreement")
    session.handle_negotiate(theirs)
    emit({"event": "negotiated", "sender": session.role, "game_uid": session.game_uid})
    if session.role == "thief":
        _send_own_turn(session, transport, emit)
    deadline = time.time() + turn_timeout
    while not session.machine.is_terminal:
        incoming = transport.poll_turn(poll_interval)
        if incoming is None:
            if time.time() > deadline:
                session.outcome = "timeout"  # opponent silent past the budget
                session.machine.advance(GameState.TECHNICAL_LOSS)
            continue
        deadline = time.time() + turn_timeout
        session.handle_receive_turn(incoming)
        if not session.machine.is_terminal:
            _send_own_turn(session, transport, emit)
    return _settle(session, transport, emit)


def _settle(session: PeerSession, transport: PeerTransport, emit: LogFn) -> PeerGameResult:
    """Exchange audits after GAME_OVER and verify theirs; skip on a technical ending."""
    outcome = session.outcome or "incomplete"
    steps = len(session.records)
    uid = session.game_uid or ""
    if session.machine.state is not GameState.GAME_OVER:
        return PeerGameResult(
            role=session.role,
            outcome=outcome,
            steps=steps,
            game_uid=uid,
            audit_ok=False,
            opponent_claim="",
            problems=(f"audit skipped: {outcome}",),
        )
    ours = build_audit(session.role, session.records, wire_result(outcome))
    emit({"event": "audit", "payload": ours})
    theirs = transport.exchange_audit(ours)
    if theirs is None:
        return PeerGameResult(
            role=session.role,
            outcome=outcome,
            steps=steps,
            game_uid=uid,
            audit_ok=False,
            opponent_claim="",
            problems=("no audit received from opponent",),
        )
    claim, problems = validate_opponent_audit(
        theirs, survival_threshold=session.constitution.movement.survival_threshold
    )
    emit(
        {
            "event": "peer_result",
            "sender": session.role,
            "payload": {"outcome": outcome, "steps": steps, "audit_ok": not problems},
        }
    )
    return PeerGameResult(
        role=session.role,
        outcome=outcome,
        steps=steps,
        game_uid=uid,
        audit_ok=not problems,
        opponent_claim=claim,
        problems=tuple(problems),
    )

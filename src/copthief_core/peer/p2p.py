"""Symmetric peer loop (M2 F1/F2): the reference's runtime shape, one loop for both roles.

No initiator exists: each peer pushes to the opponent and drains its own inboxes
(`PeerTransport`). The thief takes the first game turn; every later turn is a response to
an inbound one; audits are exchanged as pushes and verified locally. The loop is
transport-blind (queue pair in CI, FastMCP over tunnels live — PLAN §12). Settlement
(audit exchange + M5-5 profiling tail) lives in peer/settlement since M5-5 (150-line rule).
"""

from __future__ import annotations

import time

from copthief_core.domain.state_machine import GameState
from copthief_core.peer import events
from copthief_core.peer.session import NegotiationError, PeerSession
from copthief_core.peer.settlement import (
    LogFn,
    PeerGameResult,
    settle,
    validate_opponent_audit,
)
from copthief_core.peer.transport import PeerTransport

__all__ = ["LogFn", "PeerGameResult", "run_peer_game", "validate_opponent_audit"]


def _send_own_turn(session: PeerSession, transport: PeerTransport, emit: LogFn) -> None:
    """Take, log and push one of our turns (the turn token travels with it)."""
    message = session.take_turn(now=time.time())
    events.decision(emit, session)
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
    events.wire_observability(session, emit)
    theirs = transport.exchange_agreement(session.negotiate_payload())
    if theirs is None:
        raise NegotiationError("opponent never sent its agreement")
    events.inbound(emit, "agreement_received", session.role, theirs)
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
                session.machine.advance(GameState.TECHNICAL_LOSS, trigger="turn deadline exhausted")
            continue
        deadline = time.time() + turn_timeout
        events.inbound(emit, "turn_received", session.role, incoming)
        session.handle_receive_turn(incoming)
        events.belief_snapshot(emit, session)
        if not session.machine.is_terminal:
            _send_own_turn(session, transport, emit)
    return settle(session, transport, emit)

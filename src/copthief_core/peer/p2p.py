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
from copthief_core.peer import events, inbox_order
from copthief_core.peer.handshake import PairingRefusalError
from copthief_core.peer.session import NegotiationError, PeerSession
from copthief_core.peer.settlement import (
    LogFn,
    PeerGameResult,
    settle,
    validate_opponent_audit,
)
from copthief_core.peer.transport import PeerTransport, TransportError

__all__ = ["LogFn", "PeerGameResult", "run_peer_game", "validate_opponent_audit"]


def _send_own_turn(session: PeerSession, transport: PeerTransport, emit: LogFn) -> bool:
    """Take, log and push one of our turns (the turn token travels with it).

    Returns True on delivery. On transport EXHAUSTION (M7-7) it classifies our own
    technical loss and returns False — an undeliverable in-game turn is symmetric with a
    silent opponent (App E), never a naked crash into a live match and never a claim
    that the opponent lost. Any non-transport error still propagates: only a real
    delivery failure is absorbed here.
    """
    message = session.take_turn(now=time.time())
    events.decision(emit, session)
    emit({"event": "turn", "sender": session.role, "message": message})
    try:
        transport.send_turn(message)
    except TransportError as error:
        emit(
            {
                "event": "transport_error",
                "sender": session.role,
                "payload": {"reason": f"receive_turn: {error}"},
            }
        )
        session.outcome = "timeout"  # OUR technical loss — no unilateral outcome claim
        session.machine.advance(
            GameState.TECHNICAL_LOSS, trigger="outbound turn undeliverable past the turn budget"
        )
        return False
    return True


def run_peer_game(
    session: PeerSession,
    transport: PeerTransport,
    *,
    turn_timeout: float,
    poll_interval: float,
    log: LogFn | None = None,
    heartbeat: LogFn | None = None,
) -> PeerGameResult:
    """Play ONE mini-game as `session`'s role over `transport` (Input: a fresh session +
    a connected transport + the private timing budget; Output: this side's result).

    Raises NegotiationError if the handshake never completes; a protocol-violating
    inbound turn propagates after collapsing the session (PLAN §5).
    """
    emit = log or (lambda event: None)
    events.wire_observability(session, emit)
    signed = session.negotiate_payload()
    # M7-11b: a bystander's agreement — the opponent's OTHER window pushing early at
    # our one port on a role-split wire — carries the identical signed terms and fails
    # only the pairing check; it belongs to a different game. Refuse it ON THE RECORD
    # and keep waiting for our real counterpart, bounded by the turn budget (the same
    # bound the opponent's own negotiate wait declares). Terms drift and bad
    # signatures still raise on the first offense.
    handshake_deadline = time.time() + turn_timeout
    while True:
        theirs = transport.exchange_agreement(signed)
        if theirs is None:
            raise NegotiationError("opponent never sent its agreement")
        events.inbound(emit, "agreement_received", session.role, theirs)
        try:
            session.handle_negotiate(theirs)
        except PairingRefusalError as refusal:
            emit(
                {
                    "event": "agreement_refused",
                    "sender": session.role,
                    "payload": {"reason": str(refusal)},
                }
            )
            if time.time() > handshake_deadline:
                raise NegotiationError(
                    "handshake budget exhausted refusing bystander agreements: "
                    "our counterpart never arrived"
                ) from refusal
            continue
        break
    emit({"event": "negotiated", "sender": session.role, "game_uid": session.game_uid})
    # The thief's opening push happens before the loop — an undeliverable first turn is
    # classified too (M7-7), so we settle straight into the technical-loss path.
    if session.role == "thief" and not _send_own_turn(session, transport, emit):
        return settle(session, transport, emit)
    deadline = time.time() + turn_timeout
    while not session.machine.is_terminal:
        if heartbeat is not None:  # M6-7: the watchdog's liveness signal (FR-8)
            heartbeat({"event": "heartbeat"})
        # M7-8: a message held out of order outranks the wire — it is the step we are
        # waiting for, and it is already here.
        incoming = session.release_buffered() or transport.poll_turn(poll_interval)
        if incoming is not None:
            events.inbound(emit, "turn_received", session.role, incoming)
            ack = session.handle_receive_turn(incoming)
            if ack["disposition"] == inbox_order.ACCEPTED:
                deadline = time.time() + turn_timeout
                events.belief_snapshot(emit, session)
                # A reply we cannot deliver ends the game as OUR loss, not as a crash.
                if session.machine.is_terminal or _send_own_turn(session, transport, emit):
                    continue
                break
            events.tolerated(emit, session, ack["disposition"], ack["step"])
        # M7-8: ONE CLOCK PER EXPECTED MESSAGE. A redelivered or early push proves the
        # opponent is alive but does not discharge what it owes us, so it renews
        # nothing — and the deadline is judged here, on every lap, so that a flood of
        # junk cannot keep us in the loop past our own budget either.
        if time.time() > deadline:
            session.outcome = "timeout"  # opponent silent past the budget
            session.machine.advance(GameState.TECHNICAL_LOSS, trigger="turn deadline exhausted")
    return settle(session, transport, emit)

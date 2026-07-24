"""Symmetric peer transport (M2 F1): the reference's calling convention, as a seam.

The reference never composes replies into tool responses — every tool call PUSHES into
the receiver's inbox and returns a bare ack; replies arrive as the opponent's own inbound
call. This module pins that surface (`PeerTransport`) and ships the in-process queue
implementation the keyless CI match runs on; the real FastMCP adapter
(infra/p2p_transport) implements the identical protocol, so the peer loop cannot tell
transports apart (PLAN §12).
"""

from __future__ import annotations

import queue
from typing import Any, Protocol


class TransportError(RuntimeError):
    """The opponent's endpoint stayed unreachable past a push's retry budget.

    Defined at the protocol seam (M7-7) so the peer loop can classify an undeliverable
    OUTBOUND turn as its own technical loss without importing any concrete transport
    (PLAN §12). The in-process QueueTransport never raises it; the FastMCP adapter does.
    """


class InboxClosedError(RuntimeError):
    """A message arrived after this peer's own game settled (M7-10).

    Raised so the sender sees a transport failure and retries — which delivers to our
    NEXT sub-game peer — instead of an ack for a message nobody will ever read.
    """


class PeerQueues:
    """One peer's thread-safe inboxes, filled by inbound tool calls, drained by its loop."""

    def __init__(self) -> None:
        self.agreements: queue.Queue[dict[str, Any]] = queue.Queue()
        self.turns: queue.Queue[dict[str, Any]] = queue.Queue()
        self.audits: queue.Queue[dict[str, Any]] = queue.Queue()
        self.controls: queue.Queue[dict[str, Any]] = queue.Queue()
        self.closed = False

    def put(self, kind: str, message: dict[str, Any]) -> None:
        """Enqueue one inbound message (Input: the channel name + the payload; Raises:
        InboxClosedError once this peer has settled).

        Every inbound tool goes through here so the refusal is one decision rather than
        four: a peer that still took turns but refused greetings would be a peer the
        opponent could not reason about.
        """
        if self.closed:
            raise InboxClosedError(f"{kind}: this peer's game has settled; it accepts nothing more")
        inbox: queue.Queue[dict[str, Any]] = getattr(self, kind)
        inbox.put(message)

    def close(self) -> None:
        """Stop accepting new arrivals (idempotent — it is called from a `finally`).

        What is already queued stays readable: an audit that landed a moment before
        settlement still has to be verified.
        """
        self.closed = True


class PeerTransport(Protocol):
    """One peer's view of the wire: push to the opponent, pull from own inboxes."""

    def exchange_agreement(self, signed: dict[str, Any]) -> dict[str, Any] | None:
        """Send my signed agreement; block for theirs (None if it never arrives)."""
        ...

    def send_turn(self, message: dict[str, Any]) -> None:
        """Push one TurnMessage to the opponent (the turn token travels with it)."""
        ...

    def poll_turn(self, timeout: float) -> dict[str, Any] | None:
        """One pending inbound turn, or None after `timeout` seconds."""
        ...

    def exchange_audit(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        """Best-effort send of my audit; block for theirs (None if it never arrives)."""
        ...


class QueueTransport:
    """In-process half of a peer pair: writes into the OPPONENT's queues, reads its own."""

    def __init__(self, own: PeerQueues, opponent: PeerQueues, *, wait_timeout: float) -> None:
        self._own = own
        self._opponent = opponent
        self._wait_timeout = wait_timeout

    def exchange_agreement(self, signed: dict[str, Any]) -> dict[str, Any] | None:
        self._opponent.agreements.put(signed)
        return take_one(self._own.agreements, self._wait_timeout)

    def send_turn(self, message: dict[str, Any]) -> None:
        self._opponent.turns.put(message)

    def poll_turn(self, timeout: float) -> dict[str, Any] | None:
        return take_one(self._own.turns, timeout)

    def exchange_audit(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        self._opponent.audits.put(payload)
        return take_one(self._own.audits, self._wait_timeout)


def take_one(inbox: queue.Queue[dict[str, Any]], timeout: float) -> dict[str, Any] | None:
    """One queued message, or None on timeout (the poll primitive; shared with infra)."""
    try:
        return inbox.get(timeout=timeout)
    except queue.Empty:
        return None


def queue_pair(*, wait_timeout: float) -> tuple[QueueTransport, QueueTransport]:
    """Two interlocked in-process transports (Input: handshake/audit wait budget)."""
    a, b = PeerQueues(), PeerQueues()
    return (
        QueueTransport(a, b, wait_timeout=wait_timeout),
        QueueTransport(b, a, wait_timeout=wait_timeout),
    )

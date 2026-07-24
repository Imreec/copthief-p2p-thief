"""M7-7 residual: the in-game push retries on the TURN budget, not the connect budget.

The receive side tolerates a silent opponent for `turn_timeout_seconds` (180). The push
side used the same `connect_timeout_seconds` (60) for a game turn as for the handshake,
so a mid-push flap gave up three times sooner than a silent-opponent flap — an asymmetry
that had no reason to exist. `send_turn` now retries on the turn budget; the handshake
and the best-effort audit keep the connect budget. The shared `TransportError` lives at
the protocol seam so the peer loop can classify a delivery failure transport-blind.
"""

from __future__ import annotations

import time
from typing import Any

import pytest

from copthief_core.infra.p2p_transport import McpTransport
from copthief_core.peer.transport import PeerQueues, TransportError


class RecordingClient:
    """An McpToolClient stand-in: never actually reaches a peer, records the calls."""

    def __init__(self, *, fail_tools: tuple[str, ...] = ()) -> None:
        self.fail_tools = fail_tools
        self.calls: list[str] = []

    def call(self, tool: str, _payload: dict[str, Any]) -> None:
        self.calls.append(tool)
        if tool in self.fail_tools:
            raise RuntimeError(f"{tool} down")


def make_transport(client: RecordingClient) -> tuple[McpTransport, list[tuple[str, float]]]:
    """An McpTransport wired with distinct connect/turn budgets, spying on which budget
    each push uses (the wiring under test, without any wall-clock timing)."""
    budgets: list[tuple[str, float]] = []
    transport = McpTransport(
        client,
        PeerQueues(),
        connect_timeout=60.0,
        retry_interval=0.001,
        turn_push_timeout=180.0,
    )
    original = transport._push_with_retry

    def spy(tool: str, payload: dict[str, Any], *, budget: float) -> None:
        budgets.append((tool, budget))
        original(tool, payload, budget=budget)

    transport._push_with_retry = spy  # type: ignore[method-assign]
    return transport, budgets


def test_the_shared_transport_error_lives_at_the_protocol_seam() -> None:
    # Importable from the protocol module (the peer loop's import), and infra re-exports
    # the SAME type so nothing that already caught it breaks.
    from copthief_core.infra import p2p_transport

    assert p2p_transport.TransportError is TransportError


def test_send_turn_retries_on_the_turn_budget() -> None:
    transport, budgets = make_transport(RecordingClient())
    transport.send_turn({"step": 1})
    assert budgets == [("receive_turn", 180.0)]


def test_the_audit_keeps_the_connect_budget() -> None:
    client = RecordingClient()
    transport, budgets = make_transport(client)
    transport._inboxes.audits.put({"records": []})
    transport.exchange_audit({"sender": "police"})
    assert ("submit_audit", 60.0) in budgets
    assert all(b != 180.0 for _tool, b in budgets)  # nothing else borrows the turn budget


def test_the_handshake_is_bounded_by_the_connect_budget_too() -> None:
    """M7-10 gave the handshake its own re-pushing loop rather than one bounded push
    (a greeting can be swallowed by the opponent's previous sub-game peer), so the
    budget is asserted on the loop's own deadline — the guarantee is unchanged: the
    handshake never borrows the turn budget."""
    client = RecordingClient(fail_tools=("negotiate",))
    transport = McpTransport(
        client, PeerQueues(), connect_timeout=0.05, retry_interval=0.001, turn_push_timeout=180.0
    )
    started = time.monotonic()
    with pytest.raises(TransportError, match="negotiate"):
        transport.exchange_agreement({"terms": {}})
    assert time.monotonic() - started < 1.0  # the connect budget, nowhere near 180


def test_an_exhausted_push_raises_the_shared_transport_error() -> None:
    client = RecordingClient(fail_tools=("receive_turn",))
    transport = McpTransport(
        client, PeerQueues(), connect_timeout=0.02, retry_interval=0.001, turn_push_timeout=0.02
    )
    with pytest.raises(TransportError, match="receive_turn"):
        transport.send_turn({"step": 1})
    assert client.calls  # it really tried before giving up

"""Real PeerTransport over FastMCP (M2 F1): push to the opponent's URL, drain own inboxes.

Implements the exact protocol of the in-process QueueTransport (PLAN §12), so the peer
loop cannot tell transports apart. Outbound calls retry until the opponent's server is up
(peers may start seconds apart — reference behavior); the audit send is best-effort
because the opponent's process may exit right after its own final read.
"""

from __future__ import annotations

import contextlib
import time
from typing import Any

from copthief_core.infra.mcp_client import McpToolClient
from copthief_core.peer.transport import PeerQueues, take_one


class TransportError(RuntimeError):
    """The opponent's endpoint stayed unreachable past the connect budget."""


class McpTransport:
    """One peer's view of the real wire: its client to the opponent + its own inboxes."""

    def __init__(
        self,
        client: McpToolClient,
        inboxes: PeerQueues,
        *,
        connect_timeout: float,
        retry_interval: float,
    ) -> None:
        self._client = client
        self._inboxes = inboxes
        self._connect_timeout = connect_timeout
        self._retry_interval = retry_interval

    def _push_with_retry(self, tool: str, payload: dict[str, Any]) -> None:
        """Deliver one push, retrying until the opponent answers or the budget ends."""
        deadline = time.time() + self._connect_timeout
        while True:
            try:
                self._client.call(tool, payload)
            except Exception as error:  # noqa: BLE001 - transport-layer soup, bounded retry
                if time.time() >= deadline:
                    raise TransportError(f"{tool}: opponent unreachable: {error}") from error
                time.sleep(self._retry_interval)
            else:
                return

    def exchange_agreement(self, signed: dict[str, Any]) -> dict[str, Any] | None:
        self._push_with_retry("negotiate", signed)
        return take_one(self._inboxes.agreements, self._connect_timeout)

    def send_turn(self, message: dict[str, Any]) -> None:
        self._push_with_retry("receive_turn", message)

    def poll_turn(self, timeout: float) -> dict[str, Any] | None:
        return take_one(self._inboxes.turns, timeout)

    def exchange_audit(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        # Best-effort send: the opponent may already be gone; THEIR audit may still be
        # sitting in OUR inbox — always check it.
        with contextlib.suppress(TransportError):
            self._push_with_retry("submit_audit", payload)
        return take_one(self._inboxes.audits, self._connect_timeout)

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
from copthief_core.peer.transport import PeerQueues, TransportError, take_one

# M7-7: TransportError moved to the protocol seam (peer/transport) so the peer loop can
# classify a delivery failure transport-blind. Re-exported here for existing callers.
__all__ = ["McpTransport", "TransportError"]


class McpTransport:
    """One peer's view of the real wire: its client to the opponent + its own inboxes."""

    def __init__(
        self,
        client: McpToolClient,
        inboxes: PeerQueues,
        *,
        connect_timeout: float,
        retry_interval: float,
        turn_push_timeout: float,
    ) -> None:
        self._client = client
        self._inboxes = inboxes
        self._connect_timeout = connect_timeout
        self._retry_interval = retry_interval
        # M7-7: an in-game turn push retries on the TURN budget, not the connect budget —
        # a mid-push flap must tolerate as long as a silent-opponent flap does.
        self._turn_push_timeout = turn_push_timeout

    def _push_with_retry(self, tool: str, payload: dict[str, Any], *, budget: float) -> None:
        """Deliver one push, retrying until the opponent answers or `budget` ends."""
        deadline = time.time() + budget
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
        """Greet the opponent, re-greeting until the game actually starts (M7-10).

        A single push is not enough on the rolling-window protocol: the two sides finish
        a sub-game milliseconds apart, so our greeting can land in their PREVIOUS peer,
        which is still listening and exits without draining its queue. The message is
        acked, gone, and the peer waiting for it burns its whole budget — then runs ahead
        of its opponent, because failing takes less time than playing.

        So each lap pushes once and waits one retry interval for theirs. The
        classification is unchanged: never delivered is a `TransportError` (transport,
        not the peer), delivered but unanswered is `None` (their silence, which the peer
        loop judges). The cost of re-greeting a healthy-but-slow opponent is a few extra
        agreements in a queue they read once — cheap against a desynchronised series.
        """
        deadline = time.time() + self._connect_timeout
        delivered = False
        failure: Exception | None = None
        while True:
            try:
                self._client.call("negotiate", signed)
            except Exception as error:  # noqa: BLE001 - transport-layer soup, bounded
                failure = error
            else:
                delivered = True
            theirs = take_one(self._inboxes.agreements, self._retry_interval)
            if theirs is not None:
                return theirs
            if time.time() >= deadline:
                break
        if not delivered:
            raise TransportError(f"negotiate: opponent unreachable: {failure}")
        return None

    def send_turn(self, message: dict[str, Any]) -> None:
        self._push_with_retry("receive_turn", message, budget=self._turn_push_timeout)

    def poll_turn(self, timeout: float) -> dict[str, Any] | None:
        return take_one(self._inboxes.turns, timeout)

    def exchange_audit(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        # Best-effort send: the opponent may already be gone; THEIR audit may still be
        # sitting in OUR inbox — always check it.
        with contextlib.suppress(TransportError):
            self._push_with_retry("submit_audit", payload, budget=self._connect_timeout)
        return take_one(self._inboxes.audits, self._connect_timeout)

"""The watchdog's transport seam (M7-7(1)), split from peer/watchdog (150-line rule).

Wrapping the transport — rather than beating inside the peer loop — is what makes the
heartbeat measure LOOP LIVENESS instead of I/O duration: the loop's deliberate waits
become visible to the watchdog without `run_peer_game` ever learning which transport it
is holding (PLAN §12), and a future transport cannot forget to declare its waits.
"""

from __future__ import annotations

from typing import Any

from copthief_core.peer.transport import PeerTransport
from copthief_core.peer.watchdog import Watchdog


class WatchedTransport:
    """PeerTransport decorator that declares every blocking call as an I/O window.

    Input: any PeerTransport (queue pair in CI, FastMCP live) and an armed Watchdog.
    Output: the identical protocol surface, with the loop's deliberate waits visible to
    the watchdog. Wrapping at the transport — rather than beating inside the loop —
    keeps `run_peer_game` transport-blind (PLAN §12) and means a future transport
    cannot forget to declare its waits.
    """

    def __init__(self, inner: PeerTransport, watchdog: Watchdog) -> None:
        self._inner = inner
        self._watchdog = watchdog

    def exchange_agreement(self, signed: dict[str, Any]) -> dict[str, Any] | None:
        with self._watchdog.io_window():
            return self._inner.exchange_agreement(signed)

    def send_turn(self, message: dict[str, Any]) -> None:
        with self._watchdog.io_window():
            self._inner.send_turn(message)

    def poll_turn(self, timeout: float) -> dict[str, Any] | None:
        with self._watchdog.io_window():
            return self._inner.poll_turn(timeout)

    def exchange_audit(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        with self._watchdog.io_window():
            return self._inner.exchange_audit(payload)

    def poll_audit(self) -> dict[str, Any] | None:
        with self._watchdog.io_window():
            return self._inner.poll_audit()


def watched(inner: PeerTransport, watchdog: Watchdog) -> WatchedTransport:
    """The transport seam, named for the call site (`watched(transport, dog)`)."""
    return WatchedTransport(inner, watchdog)

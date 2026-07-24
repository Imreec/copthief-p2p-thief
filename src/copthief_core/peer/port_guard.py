"""One live peer per role (M7-10) — our half of the phantom-s6 find.

In the 2026-07-24 rehearsal an ORPHANED cop of ours — left alive when the shell that had
spawned it was killed — still held our port. It caught the opponent's sub-game 6 and
played it to a clean mutual audit, while our REAL sub-game 6 peer started a second later,
starved behind it, and timed out honestly. He filed that game as s6, we sealed it as s2:
one game, two indices, and nothing anywhere noticed that two of our peers were alive at
once.

The port is the contended resource, so the port is where the guard belongs. Two checks:

1. **Before starting** — if something is already listening on our port, refuse loudly.
   The peer that starves is worse than the peer that never starts: it consumes a sub-game
   of the series and reports a timeout it did not cause.
2. **After starting** — our own server must actually come up. `start_server` runs it on a
   daemon thread, so a failed bind raises where nobody is looking; that is precisely how
   the orphan's victim played on with an inbox nothing could reach.

A connect probe is used rather than a trial bind: binding to test would race the real
server for the same address, and on Windows two binds can both succeed.
"""

from __future__ import annotations

import socket
import time

__all__ = [
    "PeerAlreadyRunningError",
    "assert_role_port_free",
    "await_listening",
    "is_listening",
]

# A bind address is not a dial address: a server listening on every interface is reached
# over the loopback like any other.
_ANY_INTERFACE = {"0.0.0.0", "::", ""}  # noqa: S104 - matched, never bound
_LOOPBACK = "127.0.0.1"


class PeerAlreadyRunningError(RuntimeError):
    """Another live peer already holds this role's port (or ours never came up)."""


def is_listening(host: str, port: int, *, timeout: float) -> bool:
    """Whether anything accepts connections there (Input: address + probe budget;
    Output: True if something answered)."""
    target = _LOOPBACK if host in _ANY_INTERFACE else host
    with socket.socket() as probe:
        probe.settimeout(timeout)
        return probe.connect_ex((target, port)) == 0


def assert_role_port_free(host: str, port: int, *, role: str, timeout: float) -> None:
    """Refuse to start a second peer of this role (Raises: PeerAlreadyRunningError).

    Named for the role rather than the port because that is the rule being enforced —
    the port is merely how a second instance makes itself detectable.
    """
    if is_listening(host, port, timeout=timeout):
        raise PeerAlreadyRunningError(
            f"a live {role} peer already holds {host}:{port} — refusing to start a second "
            "one. A peer that starves behind another consumes a sub-game of the series and "
            "reports a timeout it did not cause (the 2026-07-24 phantom sub-game 6). "
            "Check for an orphaned peer: killing a shell does NOT kill what it spawned."
        )


def await_listening(host: str, port: int, *, poll_interval: float, budget: float) -> bool:
    """Wait for OUR OWN server to accept (Input: address + the poll pace and the wait
    budget, both config-owned; Output: whether it came up in time)."""
    deadline = time.monotonic() + budget
    while True:
        if is_listening(host, port, timeout=poll_interval):
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(poll_interval)

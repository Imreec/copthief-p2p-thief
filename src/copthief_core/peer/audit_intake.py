"""The stale-audit guard at settlement's front door (2026-08-19 live, ali-ahm1 g02).

The M7-10 redelivery route can land a PREVIOUS window's audit ahead of this window's
real one. An audit signed by any role other than THIS window's opponent cannot be the
opponent's — discard it LOUDLY and keep reading, or a stale echo gets verified against
live commits it can never match and an honest opponent is branded `forged` (which is
exactly what settled the ali-ahm1 friendly's sub-game 2 as a false audit failure).
A missing sender passes through: the wire validator refuses it properly as invalid.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from copthief_core.peer.transport import PeerTransport

# Bounded so a flood of echoes cannot spin settlement forever: each lap already costs
# a full transport wait budget, and one honest opponent sends at most a handful of
# retries — eight discards means something stranger than staleness is happening.
_MAX_STALE_DISCARDS = 8


def matching_audit(
    first: dict[str, Any] | None,
    transport: PeerTransport,
    *,
    own_role: str,
    emit: Callable[[dict[str, Any]], None],
) -> dict[str, Any] | None:
    """The first queued audit actually signed by this window's opponent (Input: the
    audit the exchange returned + the transport to keep polling + OUR wire role;
    Output: the matching audit, or None once the inbox runs dry). Every discard is
    emitted as `audit_stale_discarded` — evidence, never silence."""
    opponent_role = "thief" if own_role == "police" else "police"
    theirs = first
    for _ in range(_MAX_STALE_DISCARDS):
        if theirs is None or theirs.get("sender") in (None, opponent_role):
            return theirs
        emit(
            {
                "event": "audit_stale_discarded",
                "sender": own_role,
                "payload": {
                    "sender": theirs.get("sender"),
                    "result_claim": theirs.get("result_claim"),
                },
            }
        )
        theirs = transport.poll_audit()
    return None

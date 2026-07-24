"""A settled peer must stop accepting (M7-10, the other half of the swallowed handshake).

Under the rolling-window protocol our peer keeps listening from the moment its own game
settles until its process exits. In that window the opponent's NEXT sub-game peer greets
us, our dying peer accepts the greeting, enqueues it, and exits without ever draining the
queue. Their greeting is acked and gone; they then burn their whole connect budget on a
message that was delivered, and run ahead of us for the rest of the series.

Refusing after settlement turns that silent loss into an ordinary transport failure, which
their existing retry already handles by delivering to our NEXT peer. Unlike the re-push
half, this protects the direction we cannot otherwise reach: THEIR greeting to US.
"""

from __future__ import annotations

import pytest

from copthief_core.peer.transport import InboxClosedError, PeerQueues


def test_a_live_peer_accepts_on_every_channel() -> None:
    inboxes = PeerQueues()
    for kind in ("agreements", "turns", "audits", "controls"):
        inboxes.put(kind, {"hello": kind})
    assert inboxes.agreements.qsize() == 1
    assert inboxes.turns.qsize() == 1


def test_a_settled_peer_refuses_instead_of_swallowing() -> None:
    inboxes = PeerQueues()
    inboxes.close()
    with pytest.raises(InboxClosedError):
        inboxes.put("agreements", {"terms": {}})


def test_every_channel_closes_together() -> None:
    """Half-closing would be worse than not closing: a peer that still takes turns but
    refuses greetings is a peer the opponent cannot reason about."""
    inboxes = PeerQueues()
    inboxes.close()
    for kind in ("agreements", "turns", "audits", "controls"):
        with pytest.raises(InboxClosedError):
            inboxes.put(kind, {})


def test_what_was_already_queued_stays_readable() -> None:
    """Closing stops NEW arrivals; it must not destroy an audit that landed a moment
    before settlement and still has to be verified."""
    inboxes = PeerQueues()
    inboxes.put("audits", {"records": []})
    inboxes.close()
    assert inboxes.audits.get_nowait() == {"records": []}


def test_closing_twice_is_not_an_error() -> None:
    """It is called from a `finally`, and a peer that crashed mid-settlement must not
    crash again on the way out."""
    inboxes = PeerQueues()
    inboxes.close()
    inboxes.close()
    assert inboxes.closed is True

"""The handshake must survive being swallowed (M7-10).

Observed in the M7-4c live series run. Under the rolling-window protocol the two sides
finish a sub-game milliseconds apart, so the faster side starts its next peer and pushes
its agreement into the slower side's PREVIOUS peer -- which is still listening, enqueues
it, and exits without ever draining the queue. The greeting is gone, and the side waiting
for it burns its whole connect budget for a message that was delivered and thrown away.

The cost is worse than one lost sub-game: a failed handshake ends in ~60 s while a real
game takes longer, so the side that failed runs AHEAD and never re-synchronises (seen:
one side on sub-game 4 while the other was still on 2). That is two teams describing
different series -- the shape App E rule 35 zeroes both teams for.

`exchange_agreement` therefore keeps re-pushing until the game actually starts, instead
of pushing once and waiting. "Transport tolerance, no rules tolerance" (joint ADR),
applied one layer earlier than M7-8 reaches.
"""

from __future__ import annotations

from typing import Any

import pytest

from copthief_core.infra.p2p_transport import McpTransport
from copthief_core.peer.transport import PeerQueues, TransportError

AGREEMENT = {"terms": {}, "nonce": "n"}


class _Client:
    """Records pushes; `swallow` many of them vanish, as a dying peer's queue would."""

    def __init__(self, *, swallow: int = 0, unreachable: bool = False) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._swallow = swallow
        self._unreachable = unreachable
        self.inboxes: PeerQueues | None = None

    def call(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((tool, payload))
        if self._unreachable:
            raise ConnectionError("edge down")
        if self._swallow > 0:
            self._swallow -= 1  # accepted, enqueued into a queue nobody will drain
        elif self.inboxes is not None:
            self.inboxes.agreements.put({"theirs": True})
        return {"ok": True}


def _transport(client: _Client, *, budget: float = 1.0) -> McpTransport:
    inboxes = PeerQueues()
    client.inboxes = inboxes
    return McpTransport(
        client,  # type: ignore[arg-type]
        inboxes,
        connect_timeout=budget,
        retry_interval=0.01,
        turn_push_timeout=budget,
    )


def test_a_swallowed_greeting_is_pushed_again_and_the_game_starts() -> None:
    client = _Client(swallow=3)
    theirs = _transport(client).exchange_agreement(AGREEMENT)

    assert theirs == {"theirs": True}
    assert len(client.calls) == 4  # three vanished, the fourth reached a live peer
    assert {tool for tool, _ in client.calls} == {"negotiate"}


def test_the_first_push_alone_is_enough_when_nothing_is_swallowed() -> None:
    """The healthy case must not become chatty: one push, one reply, done."""
    client = _Client()
    assert _transport(client).exchange_agreement(AGREEMENT) == {"theirs": True}
    assert len(client.calls) == 1


def test_an_unreachable_opponent_still_raises_rather_than_returning_silence() -> None:
    """Unchanged classification: never delivered is a transport failure, not a peer
    that chose not to answer."""
    with pytest.raises(TransportError, match="negotiate"):
        _transport(_Client(unreachable=True), budget=0.05).exchange_agreement(AGREEMENT)


def test_a_reachable_but_silent_opponent_returns_none_within_the_budget() -> None:
    """Delivered but unanswered is the opponent's silence -- the peer loop classifies
    that itself, and must not see a TransportError instead."""
    client = _Client(swallow=10**6)
    assert _transport(client, budget=0.05).exchange_agreement(AGREEMENT) is None
    assert client.calls  # we did keep trying

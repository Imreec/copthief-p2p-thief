"""One live peer per role (M7-10) — our half of the phantom-s6 find.

In the 2026-07-24 rehearsal an ORPHANED cop of ours, left alive when the shell that
spawned it was killed, still held our port. It caught the opponent's sub-game 6 and
played it to a clean mutual audit while our REAL sub-game 6 peer, started one second
later, starved behind it and timed out honestly. He filed that game as s6; we sealed it
as s2. Same game, two indices, and nothing anywhere noticed that two of our peers were
alive at once.

The port is the contended resource, so the port is where the guard belongs. Two checks,
both bounded by config-owned budgets:

- before starting: if something is already listening on our port, refuse LOUDLY instead
  of starting a peer that will silently starve behind it;
- after starting: our own server must actually come up. It runs on a daemon thread, so a
  failed bind raises where nobody is looking — which is exactly how the orphan's victim
  played on with a dead inbox.
"""

from __future__ import annotations

import socket
from contextlib import closing

import pytest

from copthief_core.peer.port_guard import (
    PeerAlreadyRunningError,
    assert_role_port_free,
    await_listening,
    is_listening,
)

HOST = "127.0.0.1"


def _free_port() -> int:
    with closing(socket.socket()) as probe:
        probe.bind((HOST, 0))
        return int(probe.getsockname()[1])


def _listener(port: int) -> socket.socket:
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, port))
    server.listen(1)
    return server


def test_a_free_port_is_not_listening() -> None:
    assert is_listening(HOST, _free_port(), timeout=0.2) is False


def test_an_occupied_port_is_seen() -> None:
    port = _free_port()
    with closing(_listener(port)):
        assert is_listening(HOST, port, timeout=0.2) is True


def test_a_free_port_lets_the_peer_start() -> None:
    assert_role_port_free(HOST, _free_port(), role="police", timeout=0.2)  # does not raise


def test_a_second_peer_of_the_same_role_is_refused_loudly() -> None:
    """The rehearsal's exact shape: the second peer must not start and starve."""
    port = _free_port()
    with closing(_listener(port)), pytest.raises(PeerAlreadyRunningError) as refusal:
        assert_role_port_free(HOST, port, role="police", timeout=0.2)
    assert "police" in str(refusal.value)
    assert str(port) in str(refusal.value)


def test_waiting_for_our_own_server_succeeds_once_it_is_up() -> None:
    port = _free_port()
    with closing(_listener(port)):
        assert await_listening(HOST, port, poll_interval=0.02, budget=1.0) is True


def test_waiting_gives_up_when_the_server_never_binds() -> None:
    """The silent half of the same defect: `start_server` runs on a daemon thread, so a
    failed bind raises where nobody is looking and the peer plays on with a dead inbox."""
    assert await_listening(HOST, _free_port(), poll_interval=0.02, budget=0.1) is False

"""M7-7 residual: an undeliverable OUTBOUND turn is a classified loss, never a crash.

The #59 live re-drill closed the receive side — a silent opponent past our turn budget
is a clean technical loss. The push side was left open and disclosed: with the watchdog
no longer firing at 60 s, an in-game `send_turn` that exhausts its retry budget raised a
naked `TransportError` up through the loop and crashed the process. Imree approved
closing it, scoped tight:

- **in-game pushes only** — the turn push during play, not the handshake, not the audit;
- **transport-exhaustion only** — a real delivery failure, not any other exception;
- **no unilateral outcome claims** — we take OUR OWN technical loss (App E symmetry with
  the inbound deadline), we never declare that the opponent lost or that we won;
- **audit path verified** — the settlement path after a push-classified loss is exactly
  the receive-side path: audit skipped, nothing declared.
"""

from __future__ import annotations

import threading
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from copthief_core.domain.state_machine import GameState
from copthief_core.peer.p2p import run_peer_game
from copthief_core.peer.session import PeerSession
from copthief_core.peer.transport import PeerTransport, TransportError, queue_pair
from copthief_core.shared.config import load_all

CONSTITUTION, _SHIPPED, _LIMITS = load_all(Path("config"), counted=False)
PRIVATE = replace(_SHIPPED, police_class="random", thief_class="random")


class SendFails:
    """A transport whose in-game push is exhausted — the dead-edge shape after the
    retries give up. `kind` lets a test aim a NON-exhaustion failure at the same seam."""

    def __init__(self, inner: PeerTransport, *, kind: type[Exception] = TransportError) -> None:
        self._inner = inner
        self._kind = kind

    def __getattr__(self, name: str) -> Any:  # noqa: ANN401 - transparent proxy
        return getattr(self._inner, name)

    def send_turn(self, _message: dict[str, Any]) -> None:
        raise self._kind("receive_turn: opponent unreachable")


def _opening_thief(thief: PeerSession, transport: PeerTransport) -> threading.Thread:
    """A thief that handshakes and sends exactly its first turn, then goes quiet."""

    def run() -> None:
        theirs = transport.exchange_agreement(thief.negotiate_payload())
        assert theirs is not None
        thief.handle_negotiate(theirs)
        transport.send_turn(thief.take_turn(now=time.time()))

    runner = threading.Thread(target=run, name="opening-thief")
    runner.start()
    return runner


def test_an_undeliverable_reply_is_our_technical_loss_not_a_crash() -> None:
    police = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=1)
    thief = PeerSession(CONSTITUTION, PRIVATE, role="thief", seed=2)
    police_transport, thief_transport = queue_pair(wait_timeout=2.0)
    events: list[dict[str, Any]] = []
    runner = _opening_thief(thief, thief_transport)

    # The police receives the thief's opening turn, then its reply push is exhausted.
    result = run_peer_game(
        police,
        SendFails(police_transport),
        turn_timeout=2.0,
        poll_interval=0.05,
        log=events.append,
    )
    runner.join(timeout=5)

    assert result.outcome == "timeout"  # OUR loss, the technical-loss row (0/0)
    assert police.machine.state is GameState.TECHNICAL_LOSS
    assert result.opponent_claim == ""  # no claim about them — no unilateral outcome


def test_the_push_loss_names_the_push_distinctly_from_the_inbound_deadline() -> None:
    police = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=1)
    thief = PeerSession(CONSTITUTION, PRIVATE, role="thief", seed=2)
    police_transport, thief_transport = queue_pair(wait_timeout=2.0)
    events: list[dict[str, Any]] = []
    runner = _opening_thief(thief, thief_transport)
    run_peer_game(
        police, SendFails(police_transport), turn_timeout=2.0, poll_interval=0.05, log=events.append
    )
    runner.join(timeout=5)

    triggers = [
        e["payload"]["trigger"]
        for e in events
        if e.get("event") == "transition" and e["payload"]["to"] == "technical_loss"
    ]
    assert triggers, "the collapse must be logged"
    assert any("outbound" in t for t in triggers)  # NOT 'turn deadline exhausted'
    assert not any("deadline exhausted" in t for t in triggers)
    # The reason is on the record too, so an operator sees WHY the push failed.
    assert any(e.get("event") == "transport_error" for e in events)


def test_the_thiefs_undeliverable_opening_turn_is_also_classified() -> None:
    """The first push happens before the loop — it must classify too, not crash."""
    police = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=1)
    thief = PeerSession(CONSTITUTION, PRIVATE, role="thief", seed=2)
    thief_transport, police_transport = queue_pair(wait_timeout=1.0)

    def quiet_police() -> None:
        theirs = police_transport.exchange_agreement(police.negotiate_payload())
        if theirs is not None:
            police.handle_negotiate(theirs)  # then silence: we never reply

    runner = threading.Thread(target=quiet_police, name="quiet-police")
    runner.start()
    result = run_peer_game(thief, SendFails(thief_transport), turn_timeout=1.0, poll_interval=0.05)
    runner.join(timeout=5)
    assert result.outcome == "timeout"
    assert thief.machine.state is GameState.TECHNICAL_LOSS


def test_a_non_transport_error_still_propagates() -> None:
    """Scope: only transport EXHAUSTION is swallowed. A real bug in the push path must
    not be silently turned into a technical loss."""
    police = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=1)
    thief = PeerSession(CONSTITUTION, PRIVATE, role="thief", seed=2)
    police_transport, thief_transport = queue_pair(wait_timeout=2.0)
    runner = _opening_thief(thief, thief_transport)
    with pytest.raises(_BoomError, match="not a transport failure"):
        run_peer_game(
            police,
            SendFails(police_transport, kind=_BoomError),
            turn_timeout=2.0,
            poll_interval=0.05,
        )
    runner.join(timeout=5)
    assert police.machine.state is not GameState.TECHNICAL_LOSS  # not swallowed as a loss


class _BoomError(Exception):
    def __init__(self, _msg: str) -> None:
        super().__init__("not a transport failure")


def test_the_audit_path_after_a_push_loss_matches_the_inbound_deadline() -> None:
    """Audit path verified: a push-classified loss settles exactly like a silent-peer
    loss — audit skipped, no records exchanged, nothing declared."""
    police = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=1)
    thief = PeerSession(CONSTITUTION, PRIVATE, role="thief", seed=2)
    police_transport, thief_transport = queue_pair(wait_timeout=2.0)
    runner = _opening_thief(thief, thief_transport)
    result = run_peer_game(
        police, SendFails(police_transport), turn_timeout=2.0, poll_interval=0.05
    )
    runner.join(timeout=5)
    assert result.audit_ok is False
    assert result.opponent_records == 0
    assert result.problems == ("audit skipped: timeout",)

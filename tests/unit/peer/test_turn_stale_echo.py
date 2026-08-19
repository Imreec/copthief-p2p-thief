"""A redelivered PREVIOUS-window turn must not kill this window (2026-08-19 live).

The ali-ahm1 friendly, sub-game 5: their g04 thief hung, finally sent its step 12
minutes late, and the M7-10 late-retry route delivered it into our fresh g05 window —
whose role WE held as thief. `handle_receive_turn` graded the echo as this window's
opponent and collapsed on "step discontinuity: expected 1, got 12", donating the
window. The guard: a turn claiming OUR OWN role cannot come from the opponent — it is
absorbed as transport tolerance (STALE_ECHO), the turn-channel mirror of
peer/audit_intake's stale-audit guard.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from copthief_core.peer import inbox_order
from copthief_core.peer.session import PeerSession, ProtocolViolationError
from copthief_core.shared.config import load_all

CONSTITUTION, _SHIPPED, _LIMITS = load_all(Path("config"), counted=False)
PRIVATE = replace(_SHIPPED, police_class="random", thief_class="random")


def _negotiated_pair() -> tuple[PeerSession, PeerSession]:
    police = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=1)
    thief = PeerSession(CONSTITUTION, PRIVATE, role="thief", seed=2)
    police.handle_negotiate(thief.negotiate_payload())
    thief.handle_negotiate(police.negotiate_payload())
    return police, thief


def _echo_of(turn: dict[str, object], *, sender: str, step: int) -> dict[str, object]:
    """Tonight's g05 killer, reconstructed: a valid turn wearing a stale identity."""
    echo = dict(turn)
    echo["sender"] = sender
    echo["step"] = step
    return echo


def test_own_role_echo_is_tolerated_not_fatal() -> None:
    police, thief = _negotiated_pair()
    stale = _echo_of(thief.take_turn(now=0.0), sender="thief", step=12)
    fresh_thief = PeerSession(CONSTITUTION, PRIVATE, role="thief", seed=3)
    fresh_police = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=4)
    fresh_thief.handle_negotiate(fresh_police.negotiate_payload())
    fresh_police.handle_negotiate(fresh_thief.negotiate_payload())
    fresh_thief.take_turn(now=0.0)  # thief opens; then awaits the police reply
    ack = fresh_thief.handle_receive_turn(stale)
    assert ack["disposition"] == inbox_order.STALE_ECHO
    assert fresh_thief.inbound == []  # bit-identical: nothing consumed, nothing sealed
    assert not fresh_thief.machine.is_terminal


def test_the_real_opponent_still_lands_after_an_echo() -> None:
    police, thief = _negotiated_pair()
    thief_opening = thief.take_turn(now=0.0)
    stale = _echo_of(thief_opening, sender="thief", step=9)
    police.handle_receive_turn(thief_opening)
    real_reply = police.take_turn(now=0.5)
    echo_ack = thief.handle_receive_turn(stale)
    assert echo_ack["disposition"] == inbox_order.STALE_ECHO
    real_ack = thief.handle_receive_turn(real_reply)
    assert real_ack["disposition"] == inbox_order.ACCEPTED
    assert len(thief.inbound) == 1


def test_a_genuine_opponent_discontinuity_is_still_fatal() -> None:
    """The guard must not soften real violations: wrong step from the RIGHT role."""
    police, thief = _negotiated_pair()
    thief_opening = thief.take_turn(now=0.0)
    police.handle_receive_turn(thief_opening)
    flood = _echo_of(police.take_turn(now=0.5), sender="police", step=30)
    with pytest.raises(ProtocolViolationError, match="discontinuity"):
        thief.handle_receive_turn(flood)

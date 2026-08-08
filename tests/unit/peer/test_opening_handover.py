"""The opponent's opening handover must not be a technical loss (M7-53).

best2934 open every sub-game with a **nil turn at step 0** — a handover that carries no
action, after which their cop takes the first real move. gal-roy1, the only other team
they have live traffic with, opens the same way. Our receiver awaited step 1
(`expected = len(inbound) + 1`), so a step-0 arrival matched no branch in
`InboundSequencer.classify`, fell through to ILLEGAL, and `session.collapse` ruled an
immediate TECHNICAL_LOSS — on every sub-game where we play cop, which under the agreed
odd/even parity is half the series.

The tolerance is deliberately narrow, because a receiver that ignores steps is a
receiver an equivocating peer can walk through: only step 0, only before any real turn
has been consumed, only once, and it advances nothing — no seal, no belief, no machine
transition. Same shape as M7-42, where the fix was to stop reading a peer's non-game
records as game steps rather than to loosen the game-step rules themselves.
"""

from __future__ import annotations

from dataclasses import replace as _replace
from pathlib import Path

import pytest

from copthief_core.domain.state_machine import GameState
from copthief_core.peer import inbox_order
from copthief_core.peer.session import PeerSession, ProtocolViolationError
from copthief_core.shared.config import load_all

CONSTITUTION, _SHIPPED, _LIMITS = load_all(Path("config"), counted=False)
PRIVATE = _replace(_SHIPPED, police_class="random", thief_class="random")

# What their thief puts on the wire to hand the token over: a step-0 frame with no
# action. The exact field set is theirs, so the tolerance keys on the STEP alone and
# never on a field we would be guessing at.
NIL_TURN: dict[str, object] = {"step": 0, "role": "thief", "sub_game_number": 1}


def _cop() -> PeerSession:
    return PeerSession(CONSTITUTION, PRIVATE, role="police", seed=1)


def test_an_opening_handover_is_tolerated_not_collapsed() -> None:
    cop = _cop()
    ack = cop.handle_receive_turn(dict(NIL_TURN))
    assert ack["status"] == "ok"
    assert ack["disposition"] == inbox_order.HANDOVER
    assert not cop.machine.is_terminal


def test_the_handover_advances_nothing() -> None:
    """It must not consume the step we await, or their first real move reads as a
    replay and the whole sub-game slides by one."""
    cop = _cop()
    cop.handle_receive_turn(dict(NIL_TURN))
    assert cop.inbound == []
    assert cop.machine.state is not GameState.TECHNICAL_LOSS


def test_a_second_handover_is_still_a_violation() -> None:
    """Tolerating one is interop; tolerating a stream of them is a hole an equivocating
    peer walks through while our clock runs."""
    cop = _cop()
    cop.handle_receive_turn(dict(NIL_TURN))
    with pytest.raises(ProtocolViolationError):
        cop.handle_receive_turn(dict(NIL_TURN))


def test_a_step_zero_after_play_has_begun_is_a_violation() -> None:
    """Only an OPENING handover is explicable. Once real turns have been consumed a
    step-0 frame is either a bug or an attempt to rewind the game."""
    cop = _cop()
    thief = PeerSession(CONSTITUTION, PRIVATE, role="thief", seed=2)
    cop.handle_negotiate(thief.negotiate_payload())
    thief.handle_negotiate(cop.negotiate_payload())
    cop.handle_receive_turn(thief.take_turn(now=0.0))
    with pytest.raises(ProtocolViolationError):
        cop.handle_receive_turn(dict(NIL_TURN))


def test_a_real_step_one_still_lands_after_a_handover() -> None:
    """The point of the whole fix: their handover, then their cop's first real move."""
    cop = _cop()
    thief = PeerSession(CONSTITUTION, PRIVATE, role="thief", seed=2)
    cop.handle_negotiate(thief.negotiate_payload())
    thief.handle_negotiate(cop.negotiate_payload())
    cop.handle_receive_turn(dict(NIL_TURN))
    ack = cop.handle_receive_turn(thief.take_turn(now=0.0))
    assert ack["disposition"] == inbox_order.ACCEPTED
    assert len(cop.inbound) == 1

"""PeerSession: handshake gate, turn handlers, protocol-violation collapse (PLAN §4–§5)."""

from pathlib import Path

import pytest

from copthief_core.domain.state_machine import GameState
from copthief_core.peer.session import NegotiationError, PeerSession
from copthief_core.shared.config import load_all

CONSTITUTION, PRIVATE, _LIMITS = load_all(Path("config"), counted=False)


def _pair() -> tuple[PeerSession, PeerSession]:
    police = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=11)
    thief = PeerSession(CONSTITUTION, PRIVATE, role="thief", seed=22)
    return police, thief


def _handshake(police: PeerSession, thief: PeerSession) -> None:
    thief.handle_negotiate(police.negotiate_payload())
    police.handle_negotiate(thief.negotiate_payload())


def test_handshake_locks_the_same_game_uid_on_both_peers() -> None:
    police, thief = _pair()
    _handshake(police, thief)
    assert police.game_uid is not None
    assert police.game_uid == thief.game_uid


def test_handshake_refuses_value_drifted_terms() -> None:
    police, thief = _pair()
    proposal = police.negotiate_payload()
    proposal["terms"]["board_size"] = 9  # their terms no longer value-equal ours
    with pytest.raises(NegotiationError, match="terms"):
        thief.handle_negotiate(proposal)


def test_handshake_refuses_a_bad_signature() -> None:
    police, thief = _pair()
    proposal = police.negotiate_payload()
    proposal["signature"] = "0" * 64
    with pytest.raises(NegotiationError, match="signature"):
        thief.handle_negotiate(proposal)


def test_turn_exchange_advances_both_state_machines() -> None:
    police, thief = _pair()
    _handshake(police, thief)
    outbound = police.take_turn(now=1000.0)
    assert outbound["step"] == 1
    assert police.machine.state is GameState.AWAITING_REVEAL
    thief.handle_receive_turn(outbound)
    assert thief.machine.state is GameState.COMPUTING_MOVE
    reply = thief.take_turn(now=1000.5)
    police.handle_receive_turn(reply)
    assert police.machine.state is GameState.WAITING_FOR_OPPONENT


def test_malformed_inbound_turn_collapses_to_technical_loss() -> None:
    police, thief = _pair()
    _handshake(police, thief)
    outbound = police.take_turn(now=1000.0)
    del outbound["commit"]
    with pytest.raises(Exception, match="commit"):
        thief.handle_receive_turn(outbound)
    assert thief.machine.state is GameState.TECHNICAL_LOSS


def test_step_discontinuity_collapses_to_technical_loss() -> None:
    police, thief = _pair()
    _handshake(police, thief)
    outbound = police.take_turn(now=1000.0)
    outbound["step"] = 7  # replay/skip: thief expects step 1
    with pytest.raises(Exception, match="step"):
        thief.handle_receive_turn(outbound)
    assert thief.machine.state is GameState.TECHNICAL_LOSS


def test_turn_arriving_mid_computation_collapses_to_technical_loss() -> None:
    police, thief = _pair()
    _handshake(police, thief)
    outbound = police.take_turn(now=1.0)
    thief.handle_receive_turn(outbound)  # thief now COMPUTING_MOVE
    duplicate = dict(outbound)
    duplicate["step"] = 2  # passes continuity, arrives in a state that cannot accept it
    with pytest.raises(Exception, match="arrived in state"):
        thief.handle_receive_turn(duplicate)
    assert thief.machine.state is GameState.TECHNICAL_LOSS


def test_control_message_is_answered_without_touching_game_state() -> None:
    police, thief = _pair()
    _handshake(police, thief)
    before = thief.machine.state
    response = thief.handle_receive_control({"sender": "police", "action": "status"})
    assert response["status"] == "ok"
    assert thief.machine.state is before

"""PeerSession: handshake gate, turn handlers, protocol-violation collapse (PLAN §4–§5)."""

from pathlib import Path

import pytest

from copthief_core.domain.state_machine import GameState
from copthief_core.peer.session import NegotiationError, PeerSession
from copthief_core.shared.config import load_all

CONSTITUTION, _SHIPPED, _LIMITS = load_all(Path("config"), counted=False)
# Session-behavior pins probed under the M1 walk - independent of the repo's
# shipped [strategy] classes (PR #29 rule).
from dataclasses import replace as _replace  # noqa: E402

PRIVATE = _replace(_SHIPPED, police_class="random", thief_class="random")


def _pair() -> tuple[PeerSession, PeerSession]:
    # Seeds (1, 2) walk the full game without a claim landing (probed) — the survival
    # tests need that; claim tests script their own policies/claims explicitly.
    police = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=1)
    thief = PeerSession(CONSTITUTION, PRIVATE, role="thief", seed=2)
    return police, thief


def _handshake(police: PeerSession, thief: PeerSession) -> None:
    thief.handle_negotiate(police.negotiate_payload())
    police.handle_negotiate(thief.negotiate_payload())


def test_handle_negotiate_reads_the_group_from_the_identity_dict() -> None:
    from copthief_core.domain.crypto import game_uid, make_nonce, terms_signature
    from copthief_core.domain.terms import terms_from_config

    _police, thief = _pair()
    terms = terms_from_config(CONSTITUTION)
    nonce = make_nonce()
    reference_shaped = {  # exactly what the reference's Negotiation.signed() sends
        "terms": terms,
        "nonce": nonce,
        "signature": terms_signature(terms, nonce),
        "identity": {"group_id": "segal-thief-team", "group_name": "Segal-Thief-Team"},
    }
    thief.handle_negotiate(reference_shaped)
    assert thief.opponent_group == "segal-thief-team"
    assert thief.game_uid == game_uid(terms, PRIVATE.group_id, "segal-thief-team")


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


def test_thief_moves_first_police_waits() -> None:
    # M2 F2 (oracle sha 960499fd): the reference's runtime gives the THIEF the first
    # game turn; the police peer starts in the receive loop.
    police, thief = _pair()
    assert thief.machine.state is GameState.COMPUTING_MOVE
    assert police.machine.state is GameState.WAITING_FOR_OPPONENT


def test_turn_exchange_advances_both_state_machines() -> None:
    police, thief = _pair()
    _handshake(police, thief)
    outbound = thief.take_turn(now=1000.0)
    assert outbound["step"] == 1
    assert thief.machine.state is GameState.AWAITING_REVEAL
    police.handle_receive_turn(outbound)
    assert police.machine.state is GameState.COMPUTING_MOVE
    reply = police.take_turn(now=1000.5)
    thief.handle_receive_turn(reply)
    assert thief.machine.state is GameState.WAITING_FOR_OPPONENT


def _play_to_survival(police: PeerSession, thief: PeerSession) -> dict:
    """Alternate turns thief-first until the thief's survival turn; return that message."""
    threshold = CONSTITUTION.movement.survival_threshold
    for step in range(1, threshold + 1):
        message = thief.take_turn(now=float(step))
        if step == threshold:
            return message
        police.handle_receive_turn(message)
        thief.handle_receive_turn(police.take_turn(now=step + 0.5))
    raise AssertionError("unreachable")


def test_thief_survival_turn_carries_win_claim_and_ends_its_game() -> None:
    # Reference semantics: the thief's threshold-reaching turn carries
    # win_claim {"type": "survival"} and the thief's own game ends with it.
    police, thief = _pair()
    _handshake(police, thief)
    final = _play_to_survival(police, thief)
    assert final["win_claim"] == {"type": "survival"}
    assert thief.machine.state is GameState.GAME_OVER
    assert thief.outcome == "thief_survival"


def test_receiving_a_win_claim_ends_the_receiver_game() -> None:
    police, thief = _pair()
    _handshake(police, thief)
    final = _play_to_survival(police, thief)
    police.handle_receive_turn(final)
    assert police.machine.state is GameState.GAME_OVER
    assert police.outcome == "thief_survival"


def test_no_win_claim_before_the_survival_threshold() -> None:
    police, thief = _pair()
    _handshake(police, thief)
    first = thief.take_turn(now=1.0)
    assert first["win_claim"] is None
    police.handle_receive_turn(first)
    assert police.machine.state is GameState.COMPUTING_MOVE


def test_malformed_inbound_turn_collapses_to_technical_loss() -> None:
    police, thief = _pair()
    _handshake(police, thief)
    outbound = thief.take_turn(now=1000.0)
    del outbound["commit"]
    with pytest.raises(Exception, match="commit"):
        police.handle_receive_turn(outbound)
    assert police.machine.state is GameState.TECHNICAL_LOSS


def test_step_discontinuity_collapses_to_technical_loss() -> None:
    police, thief = _pair()
    _handshake(police, thief)
    outbound = thief.take_turn(now=1000.0)
    outbound["step"] = 7  # replay/skip: police expects step 1
    with pytest.raises(Exception, match="step"):
        police.handle_receive_turn(outbound)
    assert police.machine.state is GameState.TECHNICAL_LOSS


def test_turn_arriving_mid_computation_collapses_to_technical_loss() -> None:
    police, thief = _pair()
    _handshake(police, thief)
    outbound = thief.take_turn(now=1.0)
    police.handle_receive_turn(outbound)  # police now COMPUTING_MOVE
    # Continuity-clean and genuinely NEW (M7-8: a re-used commit is now absorbed as a
    # redelivery, so this fixture must carry its own seal to reach the state wall).
    early = dict(outbound) | {"step": 2, "commit": "9" * 64}
    with pytest.raises(Exception, match="arrived in state"):
        police.handle_receive_turn(early)
    assert police.machine.state is GameState.TECHNICAL_LOSS


def test_control_message_is_answered_without_touching_game_state() -> None:
    police, thief = _pair()
    _handshake(police, thief)
    before = thief.machine.state
    response = thief.handle_receive_control({"sender": "police", "kind": "status"})
    assert response["status"] == "ok"
    assert thief.machine.state is before


def test_a_signature_refusal_names_the_construction() -> None:
    """M7-54 (best2934, kit #45): "signature verification failed" tells a peer nothing
    it can act on. The construction reads three ways in prose — bare concatenation, one
    pipe, two — and only a single U+007C reproduces the kit vector. A peer that guessed
    wrong fails EVERY handshake with no diagnostic, and the natural next move is to diff
    fourteen terms that already agree. Naming the construction turns that hunt into a
    one-line fix, and costs us one string.
    """
    from copthief_core.domain.crypto import make_nonce
    from copthief_core.domain.terms import terms_from_config

    _police, thief = _pair()
    nonce = make_nonce()
    wrong = {
        "terms": terms_from_config(CONSTITUTION),
        "nonce": nonce,
        "signature": "0" * 64,  # any peer that joined with "||" or with nothing
        "identity": {"group_id": "someone", "group_name": "Someone"},
    }
    with pytest.raises(NegotiationError) as refusal:
        thief.handle_negotiate(wrong)
    text = str(refusal.value)
    assert "canonical_json(terms)|nonce" in text
    assert "single" in text.lower()

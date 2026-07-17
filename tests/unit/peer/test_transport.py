"""QueueTransport (M2 F1): the reference's push/inbox convention, in-process half."""

from copthief_core.peer.transport import queue_pair


def test_agreement_exchange_crosses_the_pair_both_ways() -> None:
    a, b = queue_pair(wait_timeout=1.0)
    mine = {"terms": {"board_size": 7}, "nonce": "aa", "signature": "s", "identity": {}}
    theirs = {"terms": {"board_size": 7}, "nonce": "bb", "signature": "t", "identity": {}}

    # Push both first (no response-carried composition anywhere), then each reads its own.
    a_opponent_view = None
    b.exchange_agreement(theirs)  # b sends; lands in a's inbox
    a_opponent_view = a.exchange_agreement(mine)  # a sends + reads b's
    assert a_opponent_view == theirs


def test_turns_travel_fifo_and_poll_times_out_to_none() -> None:
    a, b = queue_pair(wait_timeout=0.05)
    a.send_turn({"step": 1})
    a.send_turn({"step": 2})
    assert b.poll_turn(timeout=0.05) == {"step": 1}
    assert b.poll_turn(timeout=0.05) == {"step": 2}
    assert b.poll_turn(timeout=0.05) is None


def test_audit_exchange_returns_none_when_opponent_never_sends() -> None:
    a, _b = queue_pair(wait_timeout=0.05)
    assert a.exchange_audit({"sender": "police"}) is None

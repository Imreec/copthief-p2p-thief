"""Series pacing (M7-43): which sub-game index the next window opens on.

The uoh-sqak friendly (2026-08-06) died of index drift. Our driver advanced
unconditionally; theirs held. One lost handshake push put us three indices ahead and
every later window was refused on the pairing guard — correctly, and fatally.

These pins cover BOTH drift directions, because the failure we actually hit was
ASYMMETRIC: their side saw the handshake complete and timed out (a settlement, so they
advanced), ours saw nothing at all (no game, so we must hold). A hold-only rule inverts
the drift instead of removing it.
"""

from copthief_core.sdk.series_pacing import HANDSHAKE_FAILED, next_window


def _call(**kwargs: object) -> object:
    defaults = {
        "current": 2,
        "outcome": "cop_capture",
        "peer_declared": None,
        "retries_used": 0,
        "steps": 0,
        "retry_budget": 3,
        "num_games": 6,
    }
    return next_window(**{**defaults, **kwargs})  # type: ignore[arg-type]


def test_a_settled_window_advances_and_clears_the_retry_count() -> None:
    step = _call(outcome="cop_capture", retries_used=2)
    assert (step.index, step.retries_used, step.stop) == (3, 0, False)


def test_a_timeout_is_a_settlement_and_advances() -> None:
    """Agreed with uoh-sqak: a technical loss is an OUTCOME — the sub-game is over and
    scored, so the index moves. Only a window where no game happened may be retried,
    which is why this one carries turns (see the zero-turn refinement below)."""
    step = _call(outcome="timeout", steps=4)
    assert (step.index, step.stop) == (3, False)


def test_a_failed_handshake_holds_the_index_and_counts_a_retry() -> None:
    step = _call(outcome=HANDSHAKE_FAILED)
    assert (step.index, step.retries_used, step.stop) == (2, 1, False)


def test_retries_are_bounded_and_then_the_series_stops() -> None:
    step = _call(outcome=HANDSHAKE_FAILED, retries_used=3, retry_budget=3)
    assert step.stop is True


def test_we_catch_up_to_a_peer_that_is_strictly_ahead() -> None:
    """The asymmetric case that killed the friendly. They settled windows we never saw,
    so their index is real and ours is stale; those sub-games are lost but the series
    survives. Holding here would deadlock two peers on different numbers forever.
    """
    step = _call(current=2, outcome=HANDSHAKE_FAILED, peer_declared=5)
    assert (step.index, step.retries_used, step.stop) == (5, 0, False)


def test_we_never_step_backwards_to_a_peer_that_is_behind() -> None:
    """Monotonic by construction: if both sides could move either way they would
    ping-pong. A peer behind us catches up to US — we hold and let them."""
    step = _call(current=5, outcome=HANDSHAKE_FAILED, peer_declared=2)
    assert (step.index, step.retries_used) == (5, 1)


def test_a_declared_index_past_the_series_is_ignored() -> None:
    """A peer claiming sub-game 9 of 6 is confused or hostile; never follow it."""
    step = _call(current=2, outcome=HANDSHAKE_FAILED, peer_declared=9)
    assert step.index == 2


def test_catch_up_only_applies_when_no_game_happened() -> None:
    """A settled window advances by one even if the peer declared something higher —
    we have a real result for THIS index and must not skip reporting it."""
    step = _call(current=2, outcome="thief_survival", peer_declared=5)
    assert step.index == 3


def test_a_timeout_with_zero_turns_never_became_a_game_and_holds() -> None:
    """uoh-sqak's refinement (2026-08-06), and it closes a hole in the rule above.

    Their s2 completed a handshake and then timed out at zero turns. Under a bare
    settlement reading that ADVANCES — so they spent index 2 while we held it, and the
    drift opened anyway with both sides obeying the rule we had just agreed. A window
    that exchanged no turns is indistinguishable, from the other peer's side, from a
    handshake that never landed: they will hold while we spend.
    """
    step = _call(outcome="timeout", steps=0)
    assert (step.index, step.retries_used) == (2, 1)


def test_a_timeout_with_play_in_it_still_settles() -> None:
    """A technical loss with turns behind it is a real, scored outcome — replaying a
    decided sub-game is worse than the drift."""
    step = _call(outcome="timeout", steps=4)
    assert step.index == 3


def test_a_capture_settles_regardless_of_the_step_count_field() -> None:
    """Only the no-play outcomes consult `steps`; a real result is a real result."""
    assert _call(outcome="cop_capture", steps=0).index == 3

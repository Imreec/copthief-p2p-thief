"""InboundSequencer (M7-8): transport-layer at-least-once tolerance, in isolation.

The unit under test decides ONLY what a message is — a redelivery, the expected next
one, an early arrival worth holding, or a genuine violation. It never touches game
state, which is exactly why the strict state machine can stay strict behind it.
"""

from __future__ import annotations

import pytest

from copthief_core.peer.inbox_order import ACCEPTED, BUFFERED, DUPLICATE, ILLEGAL, InboundSequencer

COMMIT_A = "a" * 64
COMMIT_B = "b" * 64
COMMIT_C = "c" * 64


def _sequencer(limit: int = 2) -> InboundSequencer:
    return InboundSequencer(buffer_limit=limit)


def test_the_expected_step_is_accepted_and_remembered() -> None:
    sequencer = _sequencer()
    verdict = sequencer.classify(step=1, commit=COMMIT_A, expected=1, final_caught=False)
    assert verdict.disposition == ACCEPTED
    sequencer.record(COMMIT_A)
    assert sequencer.seen(COMMIT_A)


def test_a_redelivered_message_is_a_duplicate_not_a_violation() -> None:
    """The round-7 threat: their push landed, their ack was lost, they retried."""
    sequencer = _sequencer()
    sequencer.record(COMMIT_A)
    # `expected` has already moved on — this is exactly the shape that used to raise.
    verdict = sequencer.classify(step=1, commit=COMMIT_A, expected=2, final_caught=False)
    assert verdict.disposition == DUPLICATE


def test_a_stale_step_with_an_unseen_commit_is_still_illegal() -> None:
    """Dedup is transport tolerance, never rules tolerance: rewriting a played step
    is equivocation, and equivocation is precisely what the commit scheme exists to
    catch. Same step, different commit => the wall still stands."""
    sequencer = _sequencer()
    sequencer.record(COMMIT_A)
    verdict = sequencer.classify(step=1, commit=COMMIT_B, expected=2, final_caught=False)
    assert verdict.disposition == ILLEGAL
    assert "discontinuity" in verdict.reason


def test_the_final_caught_step_repeat_stays_exempt() -> None:
    """M5's live F10 finding: the reference seals its mandatory caught message at its
    CURRENT step. That exemption predates this sequencer and must survive it."""
    sequencer = _sequencer()
    verdict = sequencer.classify(step=4, commit=COMMIT_B, expected=5, final_caught=True)
    assert verdict.disposition == ACCEPTED


def test_an_early_step_is_buffered_not_refused() -> None:
    sequencer = _sequencer()
    verdict = sequencer.classify(step=3, commit=COMMIT_B, expected=2, final_caught=False)
    assert verdict.disposition == BUFFERED
    sequencer.hold(step=3, commit=COMMIT_B, raw={"step": 3, "commit": COMMIT_B})
    assert sequencer.release(expected=2) is None  # not due yet
    assert sequencer.release(expected=3) == {"step": 3, "commit": COMMIT_B}
    assert sequencer.release(expected=3) is None  # released exactly once


def test_a_held_step_redelivered_is_a_duplicate_but_a_swapped_commit_is_illegal() -> None:
    sequencer = _sequencer()
    sequencer.hold(step=3, commit=COMMIT_B, raw={"step": 3, "commit": COMMIT_B})
    assert (
        sequencer.classify(step=3, commit=COMMIT_B, expected=2, final_caught=False).disposition
        == DUPLICATE
    )
    swapped = sequencer.classify(step=3, commit=COMMIT_C, expected=2, final_caught=False)
    assert swapped.disposition == ILLEGAL
    assert "equivocation" in swapped.reason


def test_a_step_beyond_the_buffer_window_is_refused() -> None:
    """Bounded tolerance: the window IS the flood rule. A peer that never sends the
    step we await cannot make us hold an unbounded queue on its behalf, and there is
    no second threshold to disagree with the first."""
    sequencer = _sequencer(limit=1)
    assert sequencer.classify(step=3, commit=COMMIT_B, expected=2, final_caught=False).disposition
    verdict = sequencer.classify(step=4, commit=COMMIT_C, expected=2, final_caught=False)
    assert verdict.disposition == ILLEGAL
    assert "window" in verdict.reason


def test_holding_past_the_window_is_refused_at_the_seam_too() -> None:
    """`hold` is only ever called after `classify` blesses the step — but the bound is
    asserted there as well, so a future caller cannot grow the buffer by mistake."""
    sequencer = _sequencer(limit=1)
    sequencer.hold(step=3, commit=COMMIT_B, raw={"step": 3})
    with pytest.raises(ValueError, match="buffer"):
        sequencer.hold(step=4, commit=COMMIT_C, raw={"step": 4})


@pytest.mark.parametrize("limit", [0, -1])
def test_a_non_positive_buffer_limit_refuses_to_build(limit: int) -> None:
    with pytest.raises(ValueError, match="buffer_limit"):
        InboundSequencer(buffer_limit=limit)

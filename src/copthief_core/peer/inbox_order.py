"""Inbound sequencing (M7-8): at-least-once delivery tolerance, kept off the rules layer.

A push whose HTTP ack is lost is retried by the sender and ARRIVES TWICE — our own
M7-7 push fix retries to the full turn budget, so we are a duplicate sender by design
and every opponent may be one too. A receiver that answers a repeated step with a
protocol violation converts a flaky tunnel into a technical loss, and under App E rule
35 a contradictory pair of reports costs BOTH teams. So redelivery is handled here, at
the transport layer, and the strict state machine behind it stays strict:

* a commit we have already consumed (or already hold) is a REDELIVERY — dropped, never
  applied twice, never a violation, and never a renewal of our turn deadline;
* a step just ahead of the one we await is held in a BOUNDED window and replayed in
  order — a retry can put two of the opponent's messages in flight at once;
* a *different* commit for a step we already played is equivocation, and a step past
  the window is a flood: both stay violations. Dedup is transport tolerance, never
  rules tolerance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ACCEPTED = "accepted"
DUPLICATE = "duplicate"
BUFFERED = "buffered"
ILLEGAL = "illegal"
# M7-53: the opponent's opening nil turn — a token handover carrying no action, which
# best2934 and gal-roy1 both send at step 0 before their cop's first real move. It is
# not a game step, so it is absorbed here rather than classified as one.
HANDOVER = "handover"
# 2026-08-19 (ali-ahm1 g05 live): a redelivered PREVIOUS-window turn, recognisable
# because a genuine opponent can never send OUR OWN role. Routed here by the same
# M7-10 late-retry design the audit channel already guards against (audit_intake).
STALE_ECHO = "stale_echo"

__all__ = [
    "ACCEPTED",
    "BUFFERED",
    "DUPLICATE",
    "HANDOVER",
    "ILLEGAL",
    "STALE_ECHO",
    "InboundSequencer",
    "Verdict",
]


@dataclass(frozen=True)
class Verdict:
    """What one inbound message is (Input: see `classify`; `reason` fills for ILLEGAL)."""

    disposition: str
    reason: str = ""


class InboundSequencer:
    """One session's redelivery/reorder memory (Input: the bounded buffer window).

    Pure bookkeeping — it reads no game state and mutates none, which is what lets the
    session apply its verdict before touching the board, the belief, or the machine.
    """

    def __init__(self, *, buffer_limit: int) -> None:
        if buffer_limit < 1:
            raise ValueError(f"buffer_limit must be at least 1, got {buffer_limit}")
        self._limit = buffer_limit
        self._seen: set[str] = set()
        self._held: dict[int, tuple[str, dict[str, Any]]] = {}
        self.handover_seen = False  # M7-53: the one opening nil turn we absorb

    def seen(self, commit: str) -> bool:
        """True once `commit` has been consumed (the redelivery test)."""
        return commit in self._seen

    def record(self, commit: str) -> None:
        """Remember an ACCEPTED message's commit so its retries are recognised."""
        self._seen.add(commit)

    def classify(self, *, step: int, commit: str, expected: int, final_caught: bool) -> Verdict:
        """Decide what this message is (Input: its step + commit, the step we await,
        and whether it is the reference's mandatory caught final message — whose step
        legitimately repeats, the M5 live F10 convention; Output: a Verdict)."""
        if commit in self._seen:
            return Verdict(DUPLICATE)
        held = self._held.get(step)
        if held is not None:
            if held[0] == commit:
                return Verdict(DUPLICATE)
            return Verdict(
                ILLEGAL,
                f"commit equivocation at step {step}: a second sealed move for one step",
            )
        if step == expected or (final_caught and step == expected - 1):
            return Verdict(ACCEPTED)
        if expected < step <= expected + self._limit:
            return Verdict(BUFFERED)
        return Verdict(
            ILLEGAL,
            f"step discontinuity: expected {expected}, got {step} "
            f"(outside the {self._limit}-step buffer window)",
        )

    def hold(self, *, step: int, commit: str, raw: dict[str, Any]) -> None:
        """Buffer an early message until its predecessor lands (bound asserted here too,
        so no caller can grow the window by mistake)."""
        if step not in self._held and len(self._held) >= self._limit:
            raise ValueError(f"inbound buffer is full ({self._limit} held)")
        self._held[step] = (commit, dict(raw))

    def release(self, *, expected: int) -> dict[str, Any] | None:
        """The held message for `expected`, if one is now due (removed; released once)."""
        entry = self._held.pop(expected, None)
        return None if entry is None else entry[1]

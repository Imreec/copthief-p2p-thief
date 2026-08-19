"""Settlement must not verify a redelivered PREVIOUS-window audit (2026-08-19 live).

The ali-ahm1 friendly, sub-game 2: their g01 POLICE audit was redelivered — by our own
M7-10 route-late-retries-to-the-next-window design — into our g02 window, whose opponent
was their THIEF. `settle()` consumed the first queued audit without asking who sent it,
verified a stale police survival against g02's live thief commits, and branded an honest
opponent `forged`. The guard: an audit whose `sender` is not THIS window's opponent role
is discarded loudly, and settlement keeps polling for the right one.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from copthief_core.domain.state_machine import GameState
from copthief_core.peer.audit_flow import build_audit
from copthief_core.peer.session import PeerSession
from copthief_core.peer.settlement import settle
from copthief_core.peer.transport import queue_pair
from copthief_core.shared.config import load_all

CONSTITUTION, _SHIPPED, _LIMITS = load_all(Path("config"), counted=False)
PRIVATE = replace(_SHIPPED, police_class="random", thief_class="random")


def _short_game() -> tuple[PeerSession, PeerSession]:
    """A few honest turns, then both sessions forced to GAME_OVER for settlement."""
    police = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=1)
    thief = PeerSession(CONSTITUTION, PRIVATE, role="thief", seed=2)
    police.handle_negotiate(thief.negotiate_payload())
    thief.handle_negotiate(police.negotiate_payload())
    for turn in range(3):
        police.handle_receive_turn(thief.take_turn(now=float(turn)))
        thief.handle_receive_turn(police.take_turn(now=float(turn) + 0.5))
    forward = {
        GameState.WAITING_FOR_OPPONENT: GameState.COMPUTING_MOVE,
        GameState.COMPUTING_MOVE: GameState.COMMITTING,
        GameState.COMMITTING: GameState.AWAITING_REVEAL,
        GameState.AWAITING_REVEAL: GameState.VERIFYING,
        GameState.VERIFYING: GameState.GAME_OVER,
    }
    for session in (police, thief):
        session.outcome = "cop_capture"
        while session.machine.state is not GameState.GAME_OVER:
            session.machine.advance(forward[session.machine.state])
    return police, thief


class _Inbox:
    """Transport double: exchange_audit yields the first queued audit, poll_audit the rest."""

    def __init__(self, audits: list[dict[str, Any] | None]) -> None:
        self._audits = list(audits)

    def _next(self) -> dict[str, Any] | None:
        return self._audits.pop(0) if self._audits else None

    def exchange_audit(self, ours: dict[str, Any]) -> dict[str, Any] | None:
        return self._next()

    def poll_audit(self) -> dict[str, Any] | None:
        return self._next()


def test_stale_prior_window_audit_is_discarded_and_the_real_one_verifies() -> None:
    police, thief = _short_game()
    stale = build_audit("police", police.records, "survival")  # a PREVIOUS window's echo
    real = build_audit("thief", thief.records, "capture")
    emitted: list[dict[str, Any]] = []
    result = settle(police, _Inbox([stale, real]), emitted.append)  # type: ignore[arg-type]
    assert result.audit_ok is True
    assert result.opponent_claim == "capture"
    discarded = [e for e in emitted if e.get("event") == "audit_stale_discarded"]
    assert len(discarded) == 1
    assert discarded[0]["payload"]["sender"] == "police"


def test_stale_audit_followed_by_silence_settles_as_no_audit_not_forged() -> None:
    police, thief = _short_game()
    stale = build_audit("police", police.records, "survival")
    emitted: list[dict[str, Any]] = []
    result = settle(police, _Inbox([stale, None]), emitted.append)  # type: ignore[arg-type]
    assert result.audit_ok is False
    assert result.problems == ("no audit received from opponent",)
    assert not any("forged" in p for p in result.problems)
    assert [e for e in emitted if e.get("event") == "audit_stale_discarded"]


def test_matching_sender_passes_straight_through_unchanged() -> None:
    police, thief = _short_game()
    real = build_audit("thief", thief.records, "capture")
    emitted: list[dict[str, Any]] = []
    result = settle(police, _Inbox([real]), emitted.append)  # type: ignore[arg-type]
    assert result.audit_ok is True
    assert [e for e in emitted if e.get("event") == "audit_stale_discarded"] == []


def test_queue_transport_poll_audit_drains_and_times_out() -> None:
    ours, theirs = queue_pair(wait_timeout=0.01)
    theirs.exchange_audit({"sender": "police"})  # lands in OUR audits inbox
    assert ours.poll_audit() == {"sender": "police"}
    assert ours.poll_audit() is None  # empty inbox: budget burns, returns None

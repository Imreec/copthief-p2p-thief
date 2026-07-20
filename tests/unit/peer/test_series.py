"""M6-6 series driver (PRD_reporting §6): alternation + the M5-5 profiling carry.

Unit level via the injectable game runner: the driver's own logic — role flip per
sub-game (F2 pin: natural role on ODD sub-games), hint-trust hand-off from the
settlement `profile` event into the NEXT session, summary numbering — is pinned
without a wire in sight (the full-protocol path lives in tests/integration).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from copthief_core.peer.series import opposite_role, run_peer_series
from copthief_core.peer.settlement import PeerGameResult

LogFn = Callable[[dict[str, Any]], None]


def test_opposite_role_is_a_clean_involution() -> None:
    assert opposite_role("police") == "thief"
    assert opposite_role("thief") == "police"


class _SessionStub:
    def __init__(self, n: int, role: str, hint_trust: float | None) -> None:
        self.n, self.role, self.hint_trust = n, role, hint_trust


def _fake_play(profile_trust: dict[int, float]) -> Callable[..., PeerGameResult]:
    """A canned run_peer_game: emits a profile event for configured sub-games."""

    def play(
        session: _SessionStub,
        transport: object,
        *,
        turn_timeout: float,
        poll_interval: float,
        log: LogFn,
    ) -> PeerGameResult:
        if session.n in profile_trust:
            log(
                {
                    "event": "profile",
                    "sender": session.role,
                    "payload": {"next_hint_trust": profile_trust[session.n]},
                }
            )
        return PeerGameResult(
            role=session.role,
            outcome="thief_survival",
            steps=1,
            game_uid="uid-x",
            audit_ok=True,
            opponent_claim="survival",
            problems=(),
            opponent_records=2,
        )

    return play


def _run(num_games: int, profile_trust: dict[int, float]) -> list[_SessionStub]:
    sessions: list[_SessionStub] = []

    def make_session(n: int, role: str, hint_trust: float | None) -> _SessionStub:
        session = _SessionStub(n, role, hint_trust)
        sessions.append(session)
        return session

    def summarize(
        session: _SessionStub,
        result: PeerGameResult,
        *,
        sub_game_number: int,
        started_at: str,
        duration_seconds: float,
    ) -> dict[str, Any]:
        return {"sub_game_number": sub_game_number, "role": session.role}

    run_peer_series(
        num_games=num_games,
        natural_role="police",
        make_session=make_session,
        transport=object(),
        turn_timeout=1.0,
        poll_interval=0.1,
        play=_fake_play(profile_trust),
        summarize=summarize,
    )
    return sessions


def test_roles_alternate_natural_on_odd_sub_games() -> None:
    sessions = _run(3, profile_trust={})
    assert [s.role for s in sessions] == ["police", "thief", "police"]
    assert [s.n for s in sessions] == [1, 2, 3]


def test_profile_event_trust_reaches_the_next_session_only() -> None:
    sessions = _run(3, profile_trust={1: 0.42})
    assert sessions[0].hint_trust is None  # game 1 always starts from config default
    assert sessions[1].hint_trust == 0.42  # the M5-5 carry
    assert sessions[2].hint_trust == 0.42  # persists until a newer profile lands


def test_series_returns_paired_results_and_numbered_summaries() -> None:
    def make_session(n: int, role: str, hint_trust: float | None) -> _SessionStub:
        return _SessionStub(n, role, hint_trust)

    def summarize(
        session: _SessionStub,
        result: PeerGameResult,
        *,
        sub_game_number: int,
        started_at: str,
        duration_seconds: float,
    ) -> dict[str, Any]:
        assert started_at  # a real ISO stamp is always provided
        assert duration_seconds >= 0.0
        return {"sub_game_number": sub_game_number}

    played = run_peer_series(
        num_games=2,
        natural_role="thief",
        make_session=make_session,
        transport=object(),
        turn_timeout=1.0,
        poll_interval=0.1,
        play=_fake_play({}),
        summarize=summarize,
    )
    assert [summary["sub_game_number"] for _result, summary in played] == [1, 2]
    assert all(result.outcome == "thief_survival" for result, _summary in played)

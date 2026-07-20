"""M6-6 series driver (PRD_reporting §6; book §9 / F2 series note): one transport,
`num_games` mini-games, roles alternating — natural role on ODD sub-games.

The M5-5 profiling carry is wired here: a VERIFIED audit's settlement emits a
`profile` event whose `next_hint_trust` this driver hands to the NEXT session
(the `PeerSession(hint_trust=…)` seam; belief math untouched). The game runner
and summarizer are injectable so the driver's own logic pins keyless in unit
tests; live callers pass `run_peer_game` + `build_summary`.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from copthief_core.peer.p2p import run_peer_game
from copthief_core.peer.settlement import LogFn, PeerGameResult
from copthief_core.peer.summary_build import build_summary

MakeSession = Callable[[int, str, float | None], Any]
PlayFn = Any  # run_peer_game-shaped callable (injectable for unit tests)
SummarizeFn = Any  # build_summary-shaped callable (injectable for unit tests)


def opposite_role(role: str) -> str:
    """The other wire role (F2: roles flip each sub-game across a series)."""
    return "thief" if role == "police" else "police"


def run_peer_series(
    *,
    num_games: int,
    natural_role: str,
    make_session: MakeSession,
    transport: Any,  # noqa: ANN401 - PeerTransport protocol (or a unit-test stub)
    turn_timeout: float,
    poll_interval: float,
    log_factory: Callable[[int], LogFn | None] | None = None,
    play: PlayFn = run_peer_game,
    summarize: SummarizeFn = build_summary,
) -> list[tuple[PeerGameResult, dict[str, Any]]]:
    """Play the whole series (Input: the signed `num_games` + a session factory
    `(sub_game_number, role, hint_trust|None) -> PeerSession` + one connected
    transport; Output: per-sub-game (settlement result, reference-shaped summary)).

    Sub-game `n` plays the natural role when n is odd; the profiling carry updates
    after every verified audit and persists until a newer profile lands.
    """
    played: list[tuple[PeerGameResult, dict[str, Any]]] = []
    hint_trust: float | None = None
    for n in range(1, num_games + 1):
        role = natural_role if n % 2 == 1 else opposite_role(natural_role)
        session = make_session(n, role, hint_trust)
        sink = log_factory(n) if log_factory is not None else None
        carried: dict[str, Any] = {}

        def tee(
            event: dict[str, Any], *, _sink: LogFn | None = sink, _carried: dict[str, Any] = carried
        ) -> None:
            if event.get("event") == "profile":
                _carried.update(event.get("payload", {}))
            if _sink is not None:
                _sink(event)

        started_at = datetime.now(UTC).isoformat()
        started_clock = time.monotonic()
        result = play(
            session,
            transport,
            turn_timeout=turn_timeout,
            poll_interval=poll_interval,
            log=tee,
        )
        summary = summarize(
            session,
            result,
            sub_game_number=n,
            started_at=started_at,
            duration_seconds=round(time.monotonic() - started_clock, 1),
        )
        if isinstance(carried.get("next_hint_trust"), (int, float)):
            hint_trust = float(carried["next_hint_trust"])
        played.append((result, summary))
    return played

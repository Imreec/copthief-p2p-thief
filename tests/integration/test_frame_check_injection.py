"""M7-23 acceptance (PRD_scent §10.5): a corrupted frame in a REAL game.

A tampering transport injects one phantom cell into the first inbound grid on the
police side — the decoy class the check exists for. The game must complete normally
(refusal is evidence-grade: no technical loss, both audits clean — the grid is not
sealed, so the mutual audit never even sees it), with the refusal logged in play and
tallied at settlement.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from copthief_core.domain.state_machine import GameState
from copthief_core.peer.p2p import PeerGameResult, run_peer_game
from copthief_core.peer.session import PeerSession
from copthief_core.peer.transport import queue_pair
from copthief_core.shared.config import load_all

CONSTITUTION, PRIVATE, _LIMITS = load_all(Path("config"), counted=False)


class _TamperFirstGrid:
    """The police-side transport with one phantom cell in the first polled turn."""

    def __init__(self, inner: Any, phantom: str) -> None:  # noqa: ANN401 - Protocol wrap
        self._inner = inner
        self._phantom = phantom

    def __getattr__(self, name: str) -> Any:  # noqa: ANN401 - passthrough seam
        return getattr(self._inner, name)

    def poll_turn(self, timeout: float) -> dict[str, Any] | None:
        message = self._inner.poll_turn(timeout)
        if message is not None and message.get("step") == 1 and message.get("smell_grid"):
            message = {
                **message,
                "smell_grid": {**message["smell_grid"], self._phantom: 0.5},
            }
        return message


def _far_corner_from(cell: tuple[int, int]) -> str:
    origin = CONSTITUTION.board.axis_start_index
    last = origin + CONSTITUTION.board.grid_size - 1
    corner = max(
        [(origin, origin), (origin, last), (last, origin), (last, last)],
        key=lambda c: max(abs(c[0] - cell[0]), abs(c[1] - cell[1])),
    )
    return f"{corner[0]},{corner[1]}"


def test_injected_decoy_is_refused_and_the_game_still_settles_clean() -> None:
    police = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=11)
    thief = PeerSession(CONSTITUTION, PRIVATE, role="thief", seed=22)
    police_transport, thief_transport = queue_pair(wait_timeout=PRIVATE.connect_timeout_seconds)
    tampered = _TamperFirstGrid(police_transport, _far_corner_from(thief.position))
    events: list[dict[str, Any]] = []
    lock = threading.Lock()

    def log(event: dict[str, Any]) -> None:
        with lock:
            events.append(event)

    results: dict[str, PeerGameResult] = {}

    def play(session: PeerSession, transport: Any) -> None:  # noqa: ANN401 - Protocol
        results[session.role] = run_peer_game(
            session,
            transport,
            turn_timeout=PRIVATE.turn_timeout_seconds,
            poll_interval=PRIVATE.poll_interval_seconds,
            log=log,
        )

    threads = [
        threading.Thread(target=play, args=(police, tampered)),
        threading.Thread(target=play, args=(thief, thief_transport)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=PRIVATE.turn_timeout_seconds + PRIVATE.connect_timeout_seconds)

    # The refusal happened, in play and at settlement, on the tampered side only.
    # Step 2 refuses too — the documented baseline-poisoning cost (§10.2): the honest
    # step-2 frame pairs against the poisoned step-1 baseline; step 3 on, honest
    # traffic re-accepts on its own (self-healing, pinned by the ABSENCE of step 3+).
    refused = [e for e in events if e["event"] == "scent_frame_refused"]
    assert [e["payload"]["step"] for e in refused] == [1, 2]
    assert {e["receiver"] for e in refused} == {"police"}
    tallies = [e for e in events if e["event"] == "scent_frame_refusals"]
    assert [e["sender"] for e in tallies] == ["police"]
    assert tallies[0]["payload"]["steps"] == [1, 2]
    # Evidence-grade only: the game completed and settled clean on BOTH sides.
    assert police.machine.state is GameState.GAME_OVER
    assert thief.machine.state is GameState.GAME_OVER
    assert results["police"].outcome in ("cop_capture", "thief_survival")
    assert results["police"].outcome == results["thief"].outcome
    assert results["police"].audit_ok
    assert results["thief"].audit_ok
    assert thief.scent_refusals == []  # the untampered direction stayed silent

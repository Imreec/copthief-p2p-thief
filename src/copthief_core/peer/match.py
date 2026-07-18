"""Local mini-game runner (PLAN §13, fake-transport half): the loop the CLI calls.

Both peers run the SAME symmetric loop (peer/p2p) over an in-process queue-transport
pair — the reference's push/inbox convention with zero network — and settle with the
mutual audit. Threads appear only at the inbox seams (guidelines §15): one per peer,
joined before any result is read; the shared JSONL log is lock-guarded.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from copthief_core.domain.scoring import scores_for
from copthief_core.domain.state_machine import GameState
from copthief_core.peer.p2p import PeerGameResult, run_peer_game
from copthief_core.peer.session import PeerSession
from copthief_core.peer.transport import queue_pair
from copthief_core.shared.config import load_all, load_gazetteer
from copthief_core.shared.jsonl_logger import JsonlEventLogger


@dataclass(frozen=True)
class MatchResult:
    """Everything the M1 exit criterion asks to observe about one local mini-game."""

    outcome: str
    steps: int
    survival_threshold: int
    game_uid: str
    audit_ok_police_side: bool
    audit_ok_thief_side: bool
    police_state: GameState
    thief_state: GameState
    scores: tuple[int, int]
    survival_cop_points: int
    survival_thief_points: int
    police_moves: tuple[str, ...]
    thief_moves: tuple[str, ...]


def _locked_log(log_path: Path | None, tee: Any = None) -> Any:  # noqa: ANN401 - callable seam
    """A thread-safe event callable: file logger and/or live-view tee, one lock."""
    if log_path is None and tee is None:
        return lambda event: None
    logger = JsonlEventLogger(log_path) if log_path is not None else None
    lock = threading.Lock()

    def emit(event: dict[str, Any]) -> None:
        with lock:
            if logger is not None:
                logger.log(event)
            if tee is not None:
                tee(event)

    return emit


def run_local_minigame(
    config_dir: Path,
    *,
    police_seed: int,
    thief_seed: int,
    log_path: Path | None = None,
    tee: Any = None,  # noqa: ANN401 - optional LogFn for the live view (M4-2)
) -> MatchResult:
    """One full mini-game, both symmetric loops in-process (Input: the config tree +
    seeds + optional JSONL log path; Output: the observed MatchResult).

    With `log_path`, every sent payload is logged verbatim (PLAN §7) so the game
    replays and re-verifies from the log alone (peer/replay, M1-8). `tee` mirrors the
    same stream to the live view (M4-2)."""
    log = _locked_log(log_path, tee)
    constitution, private, _limits = load_all(config_dir, counted=False)
    gazetteer = load_gazetteer(
        config_dir / "gazetteer.json",
        map_area=constitution.world.map_area,
        board=constitution.board.make_board(),
    )
    police = PeerSession(
        constitution, private, role="police", seed=police_seed, gazetteer=gazetteer
    )
    thief = PeerSession(constitution, private, role="thief", seed=thief_seed, gazetteer=gazetteer)
    police_transport, thief_transport = queue_pair(wait_timeout=private.connect_timeout_seconds)
    log({"event": "provenance", "payload": {"police_seed": police_seed, "thief_seed": thief_seed}})

    results: dict[str, PeerGameResult] = {}

    def play(session: PeerSession, transport: Any) -> None:  # noqa: ANN401 - Protocol param
        results[session.role] = run_peer_game(
            session,
            transport,
            turn_timeout=private.turn_timeout_seconds,
            poll_interval=private.poll_interval_seconds,
            log=log,
        )

    threads = [
        threading.Thread(target=play, args=(police, police_transport), name="peer-police"),
        threading.Thread(target=play, args=(thief, thief_transport), name="peer-thief"),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=private.turn_timeout_seconds + private.connect_timeout_seconds)

    outcome = results["thief"].outcome
    scoring = constitution.scoring
    scores = scores_for(outcome, scoring)
    log(
        {
            "event": "result",
            "payload": {
                "outcome": outcome,
                "steps": results["thief"].steps,
                "game_uid": results["police"].game_uid,
                "audit_ok_police_side": results["police"].audit_ok,
                "audit_ok_thief_side": results["thief"].audit_ok,
            },
        }
    )
    return MatchResult(
        outcome=outcome,
        steps=results["thief"].steps,
        survival_threshold=constitution.movement.survival_threshold,
        game_uid=results["police"].game_uid,
        audit_ok_police_side=results["police"].audit_ok,
        audit_ok_thief_side=results["thief"].audit_ok,
        police_state=police.machine.state,
        thief_state=thief.machine.state,
        scores=scores,
        survival_cop_points=scoring.survival_cop,
        survival_thief_points=scoring.survival_thief,
        police_moves=tuple(str(r.payload["move"]) for r in police.records),
        thief_moves=tuple(str(r.payload["move"]) for r in thief.records),
    )

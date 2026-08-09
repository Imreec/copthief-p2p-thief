"""Standalone-peer flow, split from sdk/simulation (150-line rule at M5-2).

One full mini-game as a live peer: own FastMCP server, symmetric loop against the
opponent URL, optional JSONL log + live view. The facade (`SimulationSdk.run_peer`)
delegates here so consumers still see one entry point (PRD FR-14).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from copthief_core.peer.p2p import PeerGameResult, run_peer_game
from copthief_core.peer.port_guard import (
    PeerAlreadyRunningError,
    assert_role_port_free,
    await_listening,
)
from copthief_core.peer.session import PeerSession
from copthief_core.shared.budgets import io_stall_timeout
from copthief_core.shared.config import load_gazetteer
from copthief_core.shared.jsonl_logger import JsonlEventLogger

if TYPE_CHECKING:
    from copthief_core.sdk.simulation import SimulationSdk

# M7-7(2): the snapshot is an operational artifact (PRD_gatekeeper §7 D4) and is pinned
# to the git-ignored logs/ — it used to follow `log_path.parent`, so logging into a
# TRACKED directory (the kill drill logged into docs/evidence/) left a committable
# state file there. No log path can steer it now.
SNAPSHOT_DIR = Path("logs")


def snapshot_path(role: str) -> Path:
    """Where this peer's watchdog snapshot lands (Input: our wire role; Output: the
    git-ignored path — role-derived, never log-derived)."""
    return SNAPSHOT_DIR / f"state_{role}.json"


def run_peer_flow(
    sdk: SimulationSdk,
    *,
    role: str,
    seed: int,
    host: str,
    port: int,
    opponent_url: str,
    log_path: Path | None = None,
    gui: bool = False,
    sub_game_number: int | None = None,
    opponent_group: str | None = None,
) -> PeerGameResult:
    """Play ONE full mini-game as a standalone peer (blocking until it settles)."""
    from copthief_core.infra.mcp_client import McpToolClient
    from copthief_core.infra.mcp_server import start_server
    from copthief_core.infra.p2p_transport import McpTransport
    from copthief_core.peer.transport import PeerQueues

    # M7-10: one live peer per role. Refusing to start is better than starting and
    # starving behind an orphan — the starving peer consumes a sub-game and reports a
    # timeout it did not cause (the 2026-07-24 phantom sub-game 6).
    assert_role_port_free(host, port, role=role, timeout=sdk.private.poll_interval_seconds)
    inboxes = PeerQueues()
    start_server(role, inboxes, host=host, port=port)
    # ...and the server really has to be up. It runs on a daemon thread, so a failed bind
    # raises where nobody is looking, and the peer would play a whole game with an inbox
    # the opponent cannot reach.
    if not await_listening(
        host,
        port,
        poll_interval=sdk.private.poll_interval_seconds,
        budget=sdk.private.connect_timeout_seconds,
    ):
        raise PeerAlreadyRunningError(
            f"our own {role} server never began accepting on {host}:{port} — refusing to "
            "play a game whose inbox the opponent cannot reach"
        )
    transport = McpTransport(
        McpToolClient(opponent_url, timeout=sdk.private.call_timeout_seconds),
        inboxes,
        connect_timeout=sdk.private.connect_timeout_seconds,
        retry_interval=sdk.private.poll_interval_seconds,
        # M7-7: an in-game turn push tolerates a flap as long as a silent-opponent flap.
        turn_push_timeout=sdk.private.turn_timeout_seconds,
    )
    gazetteer = load_gazetteer(
        sdk.config_dir / "gazetteer.json",
        map_area=sdk.constitution.world.map_area,
        board=sdk.constitution.board.make_board(),
    )
    from copthief_core.peer.sealing import live_spec_record

    session = PeerSession(
        sdk.constitution,
        sdk.private,
        role=role,
        seed=seed,
        # M7-22: known only on a series run — lets the greeting declare the derived
        # game_uid so a wrong-input derivation refuses at T instead of at the report diff.
        expected_opponent_group=opponent_group,
        gazetteer=gazetteer,
        # M6-3: the live peer declares its sealed step-0 (real HEAD + game-count).
        # M7-4: the sub-game index must be the REAL one. It is sealed into the step-0
        # commit, so a wrong index cannot be repaired in the report afterwards — the
        # game itself carries the false claim (rules 37-38). Omitted => the configured
        # value, which is right for a one-off game and wrong for a series.
        spec_record=live_spec_record(
            sdk.private, sdk.constitution, sub_game_number=sub_game_number, role=role
        ),
    )
    sink = JsonlEventLogger(log_path).log if log_path is not None else None
    # M6-7 (FR-8): a hung live loop is never a silent freeze — the watchdog persists
    # the session snapshot (git-ignored logs/) and exits loudly after logging.
    from copthief_core.peer.watchdog import Watchdog, announce_stall, session_snapshot
    from copthief_core.peer.watchdog_transport import watched

    def stall(reason: str) -> None:  # pragma: no cover - the live stall path
        import os
        import sys

        announce_stall(reason, role=role, sink=sink, stream=sys.stdout)
        os._exit(1)  # controlled: state persisted by the watchdog before this call

    watchdog = Watchdog(
        timeout_sec=sdk.constitution.league.watchdog_timeout_sec,
        io_timeout_sec=io_stall_timeout(sdk.constitution, sdk.private),
        snapshot=lambda: session_snapshot(session),
        persist_path=snapshot_path(role),
        on_stall=stall,
    )

    def play(extra: Any = None) -> PeerGameResult:  # noqa: ANN401 - optional LogFn tee
        def fan(event: dict[str, Any]) -> None:
            if sink is not None:
                sink(event)
            if extra is not None:
                extra(event)

        watchdog.beat()
        watchdog.start(poll_interval=sdk.private.poll_interval_seconds)
        try:
            return run_peer_game(  # noqa: TRY300 - the finally below is the point
                session,
                # M7-7(1): every blocking wire call is a declared I/O window, so a dead
                # edge is measured against the I/O budget — which sits behind our own
                # turn deadline — instead of self-terminating a perfectly live loop.
                watched(transport, watchdog),
                turn_timeout=sdk.private.turn_timeout_seconds,
                poll_interval=sdk.private.poll_interval_seconds,
                log=fan,
                heartbeat=lambda _event: watchdog.beat(),
            )
        finally:
            watchdog.stop()
            # M7-10: this process keeps listening from settlement until it exits, and in
            # that window the opponent's NEXT sub-game peer greets us. Accepting there
            # swallows the greeting into a queue nobody will drain — they burn their whole
            # connect budget on a message we acked, and run ahead of us for the rest of
            # the series. Refusing makes it an ordinary transport failure, which their
            # existing retry resolves by delivering to our next peer.
            inboxes.close()

    if not gui:
        return play()
    from copthief_core.gui.windows.launch import run_with_views

    return run_with_views([role], sdk.constitution, sdk.private.gui, play)

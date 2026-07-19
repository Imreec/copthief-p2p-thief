"""Standalone-peer flow, split from sdk/simulation (150-line rule at M5-2).

One full mini-game as a live peer: own FastMCP server, symmetric loop against the
opponent URL, optional JSONL log + live view. The facade (`SimulationSdk.run_peer`)
delegates here so consumers still see one entry point (PRD FR-14).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from copthief_core.peer.p2p import PeerGameResult, run_peer_game
from copthief_core.peer.session import PeerSession
from copthief_core.shared.config import load_gazetteer
from copthief_core.shared.jsonl_logger import JsonlEventLogger

if TYPE_CHECKING:
    from copthief_core.sdk.simulation import SimulationSdk


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
) -> PeerGameResult:
    """Play ONE full mini-game as a standalone peer (blocking until it settles)."""
    from copthief_core.infra.mcp_client import McpToolClient
    from copthief_core.infra.mcp_server import start_server
    from copthief_core.infra.p2p_transport import McpTransport
    from copthief_core.peer.transport import PeerQueues

    inboxes = PeerQueues()
    start_server(role, inboxes, host=host, port=port)
    transport = McpTransport(
        McpToolClient(opponent_url),
        inboxes,
        connect_timeout=sdk.private.connect_timeout_seconds,
        retry_interval=sdk.private.poll_interval_seconds,
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
        gazetteer=gazetteer,
        # M6-3: the live peer declares its sealed step-0 (real HEAD + game-count).
        spec_record=live_spec_record(sdk.private, sdk.constitution),
    )
    sink = JsonlEventLogger(log_path).log if log_path is not None else None

    def play(extra: Any = None) -> PeerGameResult:  # noqa: ANN401 - optional LogFn tee
        def fan(event: dict[str, Any]) -> None:
            if sink is not None:
                sink(event)
            if extra is not None:
                extra(event)

        return run_peer_game(
            session,
            transport,
            turn_timeout=sdk.private.turn_timeout_seconds,
            poll_interval=sdk.private.poll_interval_seconds,
            log=fan,
        )

    if not gui:
        return play()
    from copthief_core.gui.windows.launch import run_with_views

    return run_with_views([role], sdk.constitution, sdk.private.gui, play)

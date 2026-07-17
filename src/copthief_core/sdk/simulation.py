"""SimulationSdk — the facade every consumer calls (PRD FR-14; PLAN §3).

Input: a config tree directory. Output: match results / served peers. The facade owns
process spawning for the two-process form so callers hold no transport knowledge.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from copthief_core.infra.mcp_client import McpToolClient
from copthief_core.peer.match import MatchResult, run_local_minigame
from copthief_core.peer.p2p import P2PMatchResult, drive_match
from copthief_core.peer.session import PeerSession
from copthief_core.shared.config import load_all

_READY_ATTEMPTS = 40
_READY_DELAY_SEC = 0.25


class SimulationSdk:
    """One config tree, all M1 flows (Input: config dir; see method docstrings)."""

    def __init__(self, config_dir: Path, *, counted: bool = False) -> None:
        self.config_dir = config_dir
        self.constitution, self.private, self.rate_limits = load_all(config_dir, counted=counted)

    def run_local_match(
        self, *, police_seed: int, thief_seed: int, log_path: Path | None = None
    ) -> MatchResult:
        """Full mini-game, both peers in-process over the MCP fake (keyless CI path).

        With `log_path`, the game is JSONL-logged and replayable (peer/replay, M1-8)."""
        return run_local_minigame(
            self.config_dir, police_seed=police_seed, thief_seed=thief_seed, log_path=log_path
        )

    def serve_peer(self, *, role: str, seed: int, host: str, port: int) -> None:
        """Serve one peer's four tools over real FastMCP HTTP (blocking)."""
        from copthief_core.infra.mcp_server import serve  # heavy import only when serving

        session = PeerSession(self.constitution, self.private, role=role, seed=seed)
        serve(session, host=host, port=port)

    def run_p2p_match(
        self, *, police_seed: int, thief_seed: int, thief_port: int, host: str
    ) -> P2PMatchResult:
        """The M1 exit form: spawn the thief peer as a second PROCESS, drive as police.

        The thief subprocess runs this same package's CLI (`run peer --role thief`);
        it is always terminated on the way out, pass or fail.
        """
        command = [
            sys.executable,
            "-m",
            "copthief_core.sdk.cli",
            "run",
            "peer",
            "--role",
            "thief",
            "--config",
            str(self.config_dir),
            "--seed",
            str(thief_seed),
            "--host",
            host,
            "--port",
            str(thief_port),
        ]
        thief_process = subprocess.Popen(command)  # noqa: S603 - our own interpreter+module
        try:
            client = McpToolClient(f"http://{host}:{thief_port}/mcp")
            client.wait_ready(attempts=_READY_ATTEMPTS, delay_sec=_READY_DELAY_SEC)
            return drive_match(self.config_dir, client, police_seed=police_seed)
        finally:
            thief_process.terminate()
            thief_process.wait(timeout=_READY_ATTEMPTS * _READY_DELAY_SEC)

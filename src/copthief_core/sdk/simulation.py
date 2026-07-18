"""SimulationSdk — the facade every consumer calls (PRD FR-14; PLAN §3).

Input: a config tree directory. Output: match results / played peers. The facade owns
process spawning for the two-process form so callers hold no transport knowledge. Under
the M2 F1 convention a "peer" PLAYS a full mini-game (own server + symmetric loop), it
does not passively serve tools.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from copthief_core.peer.match import MatchResult, run_local_minigame
from copthief_core.peer.p2p import PeerGameResult, run_peer_game
from copthief_core.peer.session import PeerSession
from copthief_core.shared.config import load_all, load_gazetteer
from copthief_core.shared.jsonl_logger import JsonlEventLogger
from copthief_core.strategy.referee import RefereeGameResult, play_referee_series


@dataclass(frozen=True)
class P2PMatchResult:
    """The two-process form's observable outcome (each side reports its own audit)."""

    outcome: str
    steps: int
    game_uid: str
    audit_ok_police_side: bool
    audit_ok_thief_side: bool
    scores: tuple[int, int]


class SimulationSdk:
    """One config tree, all flows (Input: config dir; see method docstrings)."""

    def __init__(self, config_dir: Path, *, counted: bool = False) -> None:
        self.config_dir = config_dir
        self.constitution, self.private, self.rate_limits = load_all(config_dir, counted=counted)

    def run_local_match(
        self, *, police_seed: int, thief_seed: int, log_path: Path | None = None
    ) -> MatchResult:
        """Full mini-game, both peers in-process over queue transports (keyless CI path).

        With `log_path`, the game is JSONL-logged and replayable (peer/replay, M1-8)."""
        return run_local_minigame(
            self.config_dir, police_seed=police_seed, thief_seed=thief_seed, log_path=log_path
        )

    def referee_series(
        self, police_brain: str, thief_brain: str, *, seeds: list[int]
    ) -> list[RefereeGameResult]:
        """Headless referee-mode series (M3-5/M3-6) — the arena's only game source."""
        return play_referee_series(
            self.constitution,
            police_brain_name=police_brain,
            thief_brain_name=thief_brain,
            smell_trust=self.private.smell_trust_weight,
            seeds=seeds,
        )

    def run_peer(
        self,
        *,
        role: str,
        seed: int,
        host: str,
        port: int,
        opponent_url: str,
        log_path: Path | None = None,
    ) -> PeerGameResult:
        """Play ONE full mini-game as a standalone peer: own FastMCP server on `port`,
        symmetric loop against `opponent_url` (blocking until the game settles)."""
        from copthief_core.infra.mcp_client import McpToolClient
        from copthief_core.infra.mcp_server import start_server
        from copthief_core.infra.p2p_transport import McpTransport
        from copthief_core.peer.transport import PeerQueues

        inboxes = PeerQueues()
        start_server(role, inboxes, host=host, port=port)
        transport = McpTransport(
            McpToolClient(opponent_url),
            inboxes,
            connect_timeout=self.private.connect_timeout_seconds,
            retry_interval=self.private.poll_interval_seconds,
        )
        gazetteer = load_gazetteer(
            self.config_dir / "gazetteer.json",
            map_area=self.constitution.world.map_area,
            board=self.constitution.board.make_board(),
        )
        session = PeerSession(
            self.constitution, self.private, role=role, seed=seed, gazetteer=gazetteer
        )
        log = JsonlEventLogger(log_path).log if log_path is not None else None
        return run_peer_game(
            session,
            transport,
            turn_timeout=self.private.turn_timeout_seconds,
            poll_interval=self.private.poll_interval_seconds,
            log=log,
        )

    def run_p2p_match(
        self, *, police_seed: int, thief_seed: int, thief_port: int, host: str
    ) -> P2PMatchResult:
        """The one-command two-process form: spawn the thief peer as a second PROCESS,
        play the police side in-process; each side reports its own audit verdict.

        The thief subprocess runs this same package's CLI; it is always reaped on the
        way out, pass or fail, and its printed result supplies the thief-side verdict.
        """
        police_port = self.private.my_port
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
            "--opponent-url",
            f"http://{host}:{police_port}/mcp",
        ]
        thief = subprocess.Popen(  # noqa: S603 - our own interpreter+module
            command, stdout=subprocess.PIPE, text=True, encoding="utf-8"
        )
        try:
            police_result = self.run_peer(
                role="police",
                seed=police_seed,
                host=host,
                port=police_port,
                opponent_url=f"http://{host}:{thief_port}/mcp",
            )
            thief_ok, thief_out = False, ""
            try:
                thief_out, _ = thief.communicate(timeout=self.private.connect_timeout_seconds)
                thief_ok = bool(json.loads(thief_out.strip().splitlines()[-1]).get("audit_ok"))
            except (subprocess.TimeoutExpired, ValueError, IndexError):
                pass  # thief verdict unavailable; reported as False, never guessed
            from copthief_core.domain.scoring import scores_for

            return P2PMatchResult(
                outcome=police_result.outcome,
                steps=police_result.steps,
                game_uid=police_result.game_uid,
                audit_ok_police_side=police_result.audit_ok,
                audit_ok_thief_side=thief_ok,
                scores=scores_for(police_result.outcome, self.constitution.scoring),
            )
        finally:
            if thief.poll() is None:
                thief.terminate()
                thief.wait(timeout=self.private.connect_timeout_seconds)

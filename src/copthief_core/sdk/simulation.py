"""SimulationSdk — the facade every consumer calls (PRD FR-14; PLAN §3).

Input: a config tree directory. Output: match results / played peers. The facade owns
process spawning for the two-process form so callers hold no transport knowledge. Under
the M2 F1 convention a "peer" PLAYS a full mini-game (own server + symmetric loop), it
does not passively serve tools.
"""

from __future__ import annotations

from pathlib import Path

from copthief_core.peer.match import MatchResult, run_local_minigame
from copthief_core.peer.p2p import PeerGameResult
from copthief_core.peer.replay import ReplaySummary
from copthief_core.sdk.p2p_match import P2PMatchResult, play_p2p_match
from copthief_core.sdk.simulation_referee import RefereeSeriesMixin
from copthief_core.shared.config import load_all
from copthief_core.shared.run_mode import RunMode


class SimulationSdk(RefereeSeriesMixin):
    """One config tree, all flows (Input: config dir; see method docstrings)."""

    def __init__(
        self, config_dir: Path, *, counted: bool = False, mode: RunMode | None = None
    ) -> None:
        self.config_dir = config_dir
        # M7-9: `mode` declares the run's governance on two axes. `counted` remains
        # the legacy spelling of "arm the App F rows" for callers that predate RunMode;
        # it can no longer imply the lecturer is reachable, which is the whole point.
        self.mode = mode if mode is not None else RunMode(strict_rules=counted)
        self.constitution, self.private, self.rate_limits = load_all(
            config_dir, counted=self.mode.strict_rules
        )

    def run_local_match(
        self,
        *,
        police_seed: int,
        thief_seed: int,
        log_path: Path | None = None,
        gui: bool = False,
    ) -> MatchResult:
        """Full mini-game, both peers in-process over queue transports (keyless CI path).

        With `log_path`, the game is JSONL-logged and replayable (peer/replay, M1-8).
        With `gui`, one live window per role renders the SAME event stream (M4-2)."""
        if not gui:
            return run_local_minigame(
                self.config_dir, police_seed=police_seed, thief_seed=thief_seed, log_path=log_path
            )
        from copthief_core.gui.windows.launch import run_with_views

        return run_with_views(
            ["police", "thief"],
            self.constitution,
            self.private.gui,
            lambda tee: run_local_minigame(
                self.config_dir,
                police_seed=police_seed,
                thief_seed=thief_seed,
                log_path=log_path,
                tee=tee,
            ),
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
        gui: bool = False,
        sub_game_number: int | None = None,
        opponent_group: str | None = None,
    ) -> PeerGameResult:
        """Play ONE full mini-game as a standalone peer: own FastMCP server on `port`,
        symmetric loop against `opponent_url` (delegates to sdk/peer_run)."""
        from copthief_core.sdk.peer_run import run_peer_flow

        return run_peer_flow(
            self,
            role=role,
            seed=seed,
            host=host,
            port=port,
            opponent_url=opponent_url,
            log_path=log_path,
            gui=gui,
            sub_game_number=sub_game_number,
            opponent_group=opponent_group,
        )

    def replay(self, log_path: Path, *, gui: bool = False) -> ReplaySummary:
        """Re-verify a logged game (M4-3; delegates to sdk/analysis)."""
        from copthief_core.sdk.analysis import replay_flow

        return replay_flow(self, log_path, gui=gui)

    def export_overlay(
        self, log_path: Path, out: Path, *, role: str | None = None
    ) -> tuple[Path, Path]:
        """Render the belief-vs-truth overlay + curve PNGs (M4-4; sdk/analysis)."""
        from copthief_core.sdk.analysis import export_overlay_flow

        return export_overlay_flow(self, log_path, out, role=role)

    def run_p2p_match(
        self, *, police_seed: int, thief_seed: int, thief_port: int, host: str
    ) -> P2PMatchResult:
        """The one-command two-process form (sdk/p2p_match): spawn the thief peer as a
        second PROCESS, play the police side in-process; each side reports its own
        audit verdict."""
        return play_p2p_match(
            self,
            police_seed=police_seed,
            thief_seed=thief_seed,
            thief_port=thief_port,
            host=host,
        )

"""SimulationSdk — the facade every consumer calls (PRD FR-14; PLAN §3).

Input: a config tree directory. Output: match results / played peers. The facade owns
process spawning for the two-process form so callers hold no transport knowledge. Under
the M2 F1 convention a "peer" PLAYS a full mini-game (own server + symmetric loop), it
does not passively serve tools.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from copthief_core.peer.match import MatchResult, run_local_minigame
from copthief_core.peer.p2p import PeerGameResult
from copthief_core.peer.replay import ReplaySummary, replay_from_log
from copthief_core.sdk.p2p_match import P2PMatchResult, play_p2p_match
from copthief_core.shared.config import load_all
from copthief_core.strategy.info_feed import BeliefFeed
from copthief_core.strategy.referee import RefereeGameResult
from copthief_core.strategy.scenarios import Scenario, play_referee_series, play_scenario_series


class SimulationSdk:
    """One config tree, all flows (Input: config dir; see method docstrings)."""

    def __init__(self, config_dir: Path, *, counted: bool = False) -> None:
        self.config_dir = config_dir
        self.constitution, self.private, self.rate_limits = load_all(config_dir, counted=counted)

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

    def referee_series(
        self, police_brain: str, thief_brain: str, *, seeds: list[int]
    ) -> list[RefereeGameResult]:
        """Headless referee-mode series on the canonical signed starts (M3-5/M3-6)."""
        return play_referee_series(
            self.constitution,
            police_brain_name=police_brain,
            thief_brain_name=thief_brain,
            smell_trust=self.private.smell_trust_weight,
            seeds=seeds,
        )

    def scenario_series(
        self,
        *,
        police: str,
        thief: str,
        scenarios: Sequence[Scenario],
        police_options: Mapping[str, float] | None = None,
        thief_options: Mapping[str, float] | None = None,
        belief_feed: BeliefFeed | None = None,
    ) -> list[RefereeGameResult]:
        """Referee-mode series over a start-scenario suite (M5-2) — the arena's and
        the DoD floors' game source; options carry per-brain config knobs, and
        `belief_feed` selects the wire-shape information structure (default hidden)."""
        return play_scenario_series(
            self.constitution,
            police_brain_name=police,
            thief_brain_name=thief,
            smell_trust=self.private.smell_trust_weight,
            scenarios=scenarios,
            police_options=police_options,
            thief_options=thief_options,
            belief_feed=belief_feed,
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
        )

    def replay(self, log_path: Path, *, gui: bool = False) -> ReplaySummary:
        """Re-verify a logged game (M4-3): the cryptographic walk over every record.

        With `gui`, the viewer window (verdict banner + step controls) opens and
        blocks until closed; the summary is returned either way."""
        summary = replay_from_log(log_path)
        if gui:
            from copthief_core.gui.windows.replay import show_replay

            show_replay(log_path, self.constitution, self.private.gui)
        return summary

    def export_overlay(
        self, log_path: Path, out: Path, *, role: str | None = None
    ) -> tuple[Path, Path]:
        """Render the belief-vs-truth overlay + error curve PNGs from an audited log
        (M4-4; post-audit only). Returns (overlay path, curve path). matplotlib is
        imported lazily — the viz group is an analysis-time dependency (D2)."""
        from copthief_core.gui.export import export_overlay_pngs

        return export_overlay_pngs(
            log_path, out, role=role, constitution=self.constitution, settings=self.private.gui
        )

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

"""Two-process p2p match flow (M1-6), split from sdk/simulation (150-line rule).

Spawns the thief peer as a second PROCESS (mandated separation), plays the police side
in-process, and reaps the child on every exit path. Each side reports its own audit
verdict — the thief's is read from its printed JSON, never guessed.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from copthief_core.domain.scoring import scores_for

if TYPE_CHECKING:  # annotation-only: simulation imports THIS module lazily at runtime
    from copthief_core.sdk.simulation import SimulationSdk


@dataclass(frozen=True)
class P2PMatchResult:
    """The two-process form's observable outcome (each side reports its own audit)."""

    outcome: str
    steps: int
    game_uid: str
    audit_ok_police_side: bool
    audit_ok_thief_side: bool
    scores: tuple[int, int]


def play_p2p_match(
    sdk: SimulationSdk, *, police_seed: int, thief_seed: int, thief_port: int, host: str
) -> P2PMatchResult:
    """One localhost mini-game across two real processes (Input: the sdk facade +
    seeds/ports; Output: the match outcome with both audit verdicts)."""
    police_port = sdk.private.my_port
    command = [
        sys.executable,
        "-m",
        "copthief_core.sdk.cli",
        "run",
        "peer",
        "--role",
        "thief",
        "--config",
        str(sdk.config_dir),
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
        police_result = sdk.run_peer(
            role="police",
            seed=police_seed,
            host=host,
            port=police_port,
            opponent_url=f"http://{host}:{thief_port}/mcp",
        )
        thief_ok, thief_out = False, ""
        try:
            thief_out, _ = thief.communicate(timeout=sdk.private.connect_timeout_seconds)
            thief_ok = bool(json.loads(thief_out.strip().splitlines()[-1]).get("audit_ok"))
        except (subprocess.TimeoutExpired, ValueError, IndexError):
            pass  # thief verdict unavailable; reported as False, never guessed
        return P2PMatchResult(
            outcome=police_result.outcome,
            steps=police_result.steps,
            game_uid=police_result.game_uid,
            audit_ok_police_side=police_result.audit_ok,
            audit_ok_thief_side=thief_ok,
            scores=scores_for(police_result.outcome, sdk.constitution.scoring),
        )
    finally:
        if thief.poll() is None:
            thief.terminate()
            thief.wait(timeout=sdk.private.connect_timeout_seconds)

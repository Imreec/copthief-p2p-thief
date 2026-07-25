"""One sub-game in its own process (M7-4): the live rolling-window protocol.

A live series plays each sub-game as a separate `copthief run peer` process — the shape
both teams played the 2026-07-24 rehearsal in, and the shape that keeps a sub-game's
server, port and inbox queues from outliving the game they belong to.

The driver spawning its own children is also half of the answer to the mis-attributed
sub-game 6 of that rehearsal: an ORPHANED peer, left alive when the shell that spawned
it was killed, held our port and played the opponent's sixth game while our real sixth
peer starved behind it. A child this process starts is a child this process reaps.

No series-side timeout is imposed. The child already ends itself on its own turn
deadline or its watchdog, both signed or config-owned; a second budget invented here
would be a quantitative value with no home in the config tree (CLAUDE.md §1 #5).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from copthief_core.peer.series import opposite_role
from copthief_core.sdk.live_series import PlaySubGame
from copthief_core.sdk.series_endpoints import SeriesEndpoints
from copthief_core.shared.run_mode import RunMode

__all__ = ["play_subgame", "subgame_command", "subgame_player"]

# How much of a dead child's stderr the run record keeps. A diagnostic display bound,
# not a game parameter — nothing in App B or App F owns it (cf. rate_limiter's
# WINDOW_SECONDS).
STDERR_LINES = 5


def _mode_flag(mode: RunMode) -> list[str]:
    """The governance flag the child must be told, if any."""
    if mode.counted_series:
        return ["--counted"]
    return ["--rehearsal"] if mode.strict_rules else []


def subgame_command(
    *,
    role: str,
    config_dir: Path,
    seed: int,
    host: str,
    port: int,
    opponent_url: str,
    log_path: Path,
    sub_game_number: int,
    mode: RunMode,
) -> list[str]:
    """The argv for one sub-game child (Input: everything the peer needs plus the run's
    governance; Output: the command).

    The governance flag rides along because the child loads the config tree itself: a
    driver that armed the App F rows only in its own process would play every sub-game
    under the disarmed loader, which is the M7-9 defect merely relocated.
    """
    return [
        sys.executable,
        "-m",
        "copthief_core.sdk.cli",
        "run",
        "peer",
        "--role",
        role,
        "--config",
        str(config_dir),
        "--seed",
        str(seed),
        "--host",
        host,
        "--port",
        str(port),
        "--opponent-url",
        opponent_url,
        "--log",
        str(log_path),
        "--sub-game",
        str(sub_game_number),
        *_mode_flag(mode),
    ]


def play_subgame(command: list[str]) -> dict[str, Any]:
    """Run one sub-game child to completion (Input: its argv; Output: the peer's own
    printed result, or a recorded failure carrying the reason).

    A child that dies without a parseable verdict is NOT reported as a played game: the
    outcome is left unknown and the log it did or did not leave is what the series
    aggregation judges. Nothing here guesses on a peer's behalf.

    Its stderr is kept, because the first live run of the driver ended with five
    sub-games "played" in three seconds and a record that said only `unknown` — a series
    that cannot say WHY a sub-game did not happen cannot be operated.
    """
    child = subprocess.run(  # noqa: S603 - our own interpreter running our own module
        command, capture_output=True, text=True, encoding="utf-8", check=False
    )
    lines = [line for line in (child.stdout or "").splitlines() if line.strip()]
    try:
        result: dict[str, Any] = json.loads(lines[-1])
    except (IndexError, ValueError):
        return {
            "outcome": "unknown",
            "steps": 0,
            "audit_ok": False,
            "exit_code": child.returncode,
            "stderr": _tail(child.stderr),
        }
    result["exit_code"] = child.returncode
    return result


def _tail(stderr: str | None) -> str:
    """The last lines of a dead child's stderr — enough to name the cause in the run
    record without pasting a whole traceback into a JSON field."""
    lines = [line for line in (stderr or "").splitlines() if line.strip()]
    return "\n".join(lines[-STDERR_LINES:])


def subgame_player(
    *, config_dir: Path, host: str, port: int, endpoints: SeriesEndpoints, mode: RunMode
) -> PlaySubGame:
    """Bind the network settings once and hand the driver a player (Input: the peer's
    fixed settings, the opponent's endpoints and the run's governance; Output: a
    `PlaySubGame`).

    Keeps `sdk/live_series` free of transport knowledge — it decides WHICH sub-game is
    played next, never how a peer reaches the wire. The URL follows the OPPONENT'S
    role each sub-game (M7-11): a role-split opponent serves two services, and dialing
    the wrong one burns the whole connect budget before failing.
    """

    def play(*, sub_game_number: int, role: str, log_path: Path, seed: int) -> dict[str, Any]:
        return play_subgame(
            subgame_command(
                role=role,
                config_dir=config_dir,
                seed=seed,
                host=host,
                port=port,
                opponent_url=endpoints.for_opponent_role(opposite_role(role)),
                log_path=log_path,
                sub_game_number=sub_game_number,
                mode=mode,
            )
        )

    return play

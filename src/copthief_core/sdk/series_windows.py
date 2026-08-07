"""Playing a series' windows in order (M7-43) — the loop, split from the driver.

`sdk/live_series` owns the series' CONTRACT (preflight, artifact, the one report);
this owns the far smaller question of which window runs next and which of them count.
Split when the pacing rules pushed the driver past the 150-line rule — split, never
compress (CLAUDE.md §1 #1).

The rules themselves are pure and live in `sdk/series_pacing`; this is the I/O-side loop
that applies them.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from copthief_core.peer.series import opposite_role
from copthief_core.sdk.series_pacing import became_a_game, declared_index, next_window

if TYPE_CHECKING:
    from copthief_core.sdk.live_series import PlaySubGame

__all__ = ["WindowRun", "missing_sub_games", "play_windows"]


def missing_sub_games(played: list[dict[str, Any]], expected: int) -> list[int]:
    """Which of the `expected` sub-games never settled (Output: their indices, ascending).

    M7-43b: completeness is CHECKED, not assumed. It used to be a side effect of the
    loop's shape — a `for n in range(...)` could only hand the artifact builder a full
    set, so the builder's own "does every log settle?" check was sufficient by accident.
    A loop that can stop early hands it a set that is consistent and INCOMPLETE, and the
    driver mailed a two-sub-game "series tie" for a six-game match (uoh-sqak, 2026-08-07).
    """
    settled = {int(row["sub_game_number"]) for row in played}
    return [n for n in range(1, expected + 1) if n not in settled]


@dataclass
class WindowRun:
    """Everything the driver needs from the windows it played."""

    played: list[dict[str, Any]] = field(default_factory=list)
    logs: list[Path] = field(default_factory=list)
    durations: dict[int, float] = field(default_factory=dict)


def play_windows(
    *,
    play: PlaySubGame,
    log_path_for: Any,  # noqa: ANN401 - Callable[[int], Path], kept loose for the seam
    natural_role: str,
    num_games: int,
    retry_budget: int,
    seed: int,
) -> WindowRun:
    """Play the series' windows to completion (Input: the sub-game player, a log-path
    factory, our natural role and the pacing budgets; Output: the rows, logs and
    durations of the windows that actually became games).

    A window that never became a game contributes NO row and NO log: the series record
    must describe sub-games that happened, not attempts to start one. Every window that
    does produce a result is played to the end — abandoning a series early leaves the
    opponent playing a match we quit.
    """
    run = WindowRun()
    index, retries = 1, 0
    while index <= num_games:
        # F2: the natural role plays the odd sub-games, so a six-game series splits 3/3.
        role = natural_role if index % 2 else opposite_role(natural_role)
        log_path = log_path_for(index)
        started = time.monotonic()
        result = play(sub_game_number=index, role=role, log_path=log_path, seed=seed + index)
        outcome = str(result.get("outcome", ""))
        steps = int(result.get("steps", 0) or 0)
        if became_a_game(outcome, steps):
            run.durations[index] = round(time.monotonic() - started, 1)
            run.logs.append(log_path)
            run.played.append({"sub_game_number": index, "role": role, **result})
        step = next_window(
            current=index,
            outcome=outcome,
            steps=steps,
            peer_declared=declared_index(result),
            retries_used=retries,
            retry_budget=retry_budget,
            num_games=num_games,
        )
        if step.stop:
            break
        index, retries = step.index, step.retries_used
    return run

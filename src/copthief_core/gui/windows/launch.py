"""Launch glue (coverage-omitted shell): wire a game runner to live view windows.

The sdk calls `run_with_views` with the game as a closure over a tee LogFn; every
event the game logs is also fanned to each window's queue — the SAME stream the JSONL
archives, which is what makes the live view local-truth-safe by construction
(PRD_gui_replay §4).
"""

from __future__ import annotations

import queue
from collections.abc import Callable
from typing import Any

from copthief_core.gui.models.live import LiveViewModel
from copthief_core.gui.windows.live import LiveView, run_live_views
from copthief_core.shared.config_model import Constitution, GuiSettings

LogFn = Callable[[dict[str, Any]], None]


def run_with_views[T](
    roles: list[str],
    constitution: Constitution,
    settings: GuiSettings,
    run: Callable[[LogFn], T],
) -> T:
    """Open one live window per role, run the game, return its result (Input: the
    roles to view + signed geometry + render knobs + the game closure; Output: the
    closure's result; Raises: RuntimeError if the operator closes the view first)."""
    board = constitution.board.make_board()
    queues: list[queue.Queue[dict[str, Any]]] = [queue.Queue() for _ in roles]
    views = [
        LiveView(
            model=LiveViewModel(
                role=role,
                board=board,
                start=(
                    constitution.board.cop_start
                    if role == "police"
                    else constitution.board.thief_start
                ),
            ),
            events=events,
            board=board,
            settings=settings,
            title=f"copthief {role} - live (local truth)",
        )
        for role, events in zip(roles, queues, strict=True)
    ]

    def tee(event: dict[str, Any]) -> None:
        for events in queues:
            events.put(event)

    box: dict[str, T] = {}

    def play() -> None:
        box["result"] = run(tee)

    run_live_views(views, play)
    if "result" not in box:
        raise RuntimeError("live view closed before the game settled - no result to report")
    return box["result"]

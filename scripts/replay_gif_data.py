"""Log parsing for the replay-GIF renderer (split from render_replay_gif at the 150-line rule).

Display-only tolerance beyond `peer.scent_records`: a peer whose `state` is a
JSON-encoded string (the ali-ahm1 form) is decoded here so their walk can be DRAWN;
verdict-relevant readers keep their stricter shape test.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from copthief_core.peer.scent_records import POSITION_KEYS, as_cell  # noqa: E402

_STEP = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "W": (0, -1)}


def cell_of(payload: dict[str, Any]) -> tuple[int, int] | None:
    """The revealed cell, tolerating the JSON-string `state` form (display-only)."""
    for key in POSITION_KEYS:
        value = payload.get(key)
        if isinstance(value, str):
            try:
                value = json.loads(value).get("pos")
            except (ValueError, AttributeError):
                continue
        cell = as_cell(value)
        if cell is not None:
            return cell
    return None


def post_move_path(records: list[dict[str, Any]]) -> dict[int, tuple[int, int]]:
    """Each audited step's POST-move cell (Input: one role's revealed records;
    Output: step -> (row, col); the sealed step-0 declaration is skipped).

    Our own records carry `position` already post-move; a peer's `state` form is
    the pre-move snapshot, so its `action` is applied to reach the same convention.
    """
    path: dict[int, tuple[int, int]] = {}
    for record in records:
        payload = record["payload"]
        step = payload.get("step")
        if not isinstance(step, int) or step < 1:
            continue
        position = as_cell(payload.get("position"))
        if position is not None:
            path[step] = position
            continue
        cell = cell_of(payload)
        if cell is None:
            continue
        delta = _STEP.get(payload.get("action", "STAY"), (0, 0))
        path[step] = (cell[0] + delta[0], cell[1] + delta[1])
    return path


def barriers_by_step(events: list[dict[str, Any]]) -> dict[int, tuple[int, int]]:
    """Wall placements by step, from both sides' verbatim turn messages."""
    walls: dict[int, tuple[int, int]] = {}
    for event in events:
        if event["event"] not in ("turn", "turn_received"):
            continue
        message = event.get("message") or event.get("raw") or {}
        placed = message.get("barrier_placed")
        if isinstance(placed, list):
            walls[message["step"]] = (placed[0], placed[1])
    return walls

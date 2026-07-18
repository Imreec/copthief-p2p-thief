"""Replay walk model (PRD_gui_replay §5): the viewer's step cursor, pure and tested.

Frames are built from POST-AUDIT revealed records only — rendering the objective board
retrospectively is legal (App E rules 8–9 constrain the LIVE view; book §7.2 draws
exactly this line). The verdict banner travels with the walk so the window shows the
book's binary outcome above the timeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from copthief_core.peer.replay import (
    replay_from_log,
    revealed_records,
    verdict_for,
    wire_turns,
)
from copthief_core.shared.jsonl_logger import read_events

Coord = tuple[int, int]


@dataclass(frozen=True)
class ReplayFrame:
    """One step of the audited timeline (both sides' revealed truth)."""

    step: int
    positions: dict[str, Coord | None]
    moves: dict[str, str | None]
    hints: dict[str, str | None]
    barriers: frozenset[Coord]


class ReplayWalk:
    """Forward/back cursor over the verified timeline (book §7.4 control buttons)."""

    def __init__(self, frames: list[ReplayFrame], verdict: str, problems: list[str]) -> None:
        self._frames = frames
        self.verdict = verdict
        self.problems = problems
        self.index = 0

    @classmethod
    def from_log(cls, path: Path) -> ReplayWalk:
        """Build the walk by re-verifying the log (Input: JSONL path; Output: a walk
        carrying the banner verdict, every problem found, and the audited frames)."""
        summary = replay_from_log(path)
        events = read_events(path)
        return cls(_frames(events), verdict_for(summary), summary.problems)

    def __len__(self) -> int:
        return len(self._frames)

    def frame(self, index: int) -> ReplayFrame:
        """The frame at `index` (0-based)."""
        return self._frames[index]

    def current(self) -> ReplayFrame:
        """The frame under the cursor."""
        return self._frames[self.index]

    def forward(self) -> None:
        """Step the cursor forward, clamped at the last frame."""
        self.index = min(self.index + 1, len(self._frames) - 1)

    def back(self) -> None:
        """Step the cursor back, clamped at the first frame."""
        self.index = max(self.index - 1, 0)


def _coord(value: Any) -> Coord | None:  # noqa: ANN401 - logged JSON value
    if isinstance(value, list | tuple) and len(value) == 2:
        return (int(value[0]), int(value[1]))
    return None


def _frames(events: list[dict[str, Any]]) -> list[ReplayFrame]:
    """The audited timeline: per step, each side's revealed record + declared barriers."""
    by_step: dict[int, dict[str, dict[str, Any]]] = {}
    for sender, records in revealed_records(events).items():
        for record in records:
            step = record["payload"].get("step")
            if isinstance(step, int):
                by_step.setdefault(step, {})[sender] = record["payload"]
    declared: dict[int, list[Coord]] = {}
    for turn in wire_turns(events):
        cell = _coord(turn["message"].get("barrier_placed"))
        step = turn["message"].get("step")
        if cell is not None and isinstance(step, int):
            declared.setdefault(step, []).append(cell)
    frames, barriers = [], set()
    for step in sorted(by_step):
        barriers.update(declared.get(step, []))
        sides = by_step[step]
        frames.append(
            ReplayFrame(
                step=step,
                positions={s: _coord(p.get("position")) for s, p in sides.items()},
                moves={s: p.get("move") for s, p in sides.items()},
                hints={s: p.get("hint") for s, p in sides.items()},
                barriers=frozenset(barriers),
            )
        )
    return frames

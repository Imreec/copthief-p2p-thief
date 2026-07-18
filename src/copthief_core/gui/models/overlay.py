"""Belief-vs-truth overlay series (PRD_gui_replay §6): pure data prep, post-audit only.

Truth is the opponent's REVEALED audit trajectory — available exactly when an audit is
in the log, never before (FR-10). Belief history is the logged `belief` snapshots:
evidence of what we believed at the time, immune to later model drift. Per-step error
is `1 − P(truth_cell)` — metric-identical to `BeliefFilter.belief_error` and the M3-3
eval tables, so every curve in the README speaks one language.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from copthief_core.peer.replay import revealed_records

Coord = tuple[int, int]
_ROLES = ("police", "thief")


@dataclass(frozen=True)
class OverlaySeries:
    """One audited game's belief-vs-truth timeline, ready to render."""

    role: str
    opponent: str
    steps: list[int]
    errors: list[float]
    truth_path: list[Coord]
    beliefs: list[dict[str, float]]


def overlay_series(events: list[dict[str, Any]], *, role: str | None) -> OverlaySeries:
    """Align belief snapshots with the audited truth (Input: logged events + whose
    belief to plot, None = auto-detect the single logged role; Output: the series;
    Raises: ValueError without an opponent audit or without belief snapshots)."""
    detected = role if role is not None else _single_belief_role(events)
    opponent = _ROLES[0] if detected == _ROLES[1] else _ROLES[1]
    revealed = revealed_records(events).get(opponent)
    if not revealed:
        raise ValueError(f"no {opponent} audit in the log - the overlay is post-audit only (FR-10)")
    truth_by_step: dict[int, Coord] = {
        r["payload"]["step"]: (r["payload"]["position"][0], r["payload"]["position"][1])
        for r in revealed
        if isinstance(r["payload"].get("step"), int)
    }
    snapshots = [
        e["payload"] for e in events if e["event"] == "belief" and e.get("sender") == detected
    ]
    aligned = [s for s in snapshots if s["step"] in truth_by_step]
    if not aligned:
        raise ValueError(f"no belief snapshots for {detected} align with the audited steps")
    steps = [s["step"] for s in aligned]
    truth_path = [truth_by_step[s] for s in steps]
    beliefs: list[dict[str, float]] = [dict(s["grid"]) for s in aligned]
    errors = [
        1.0 - grid.get(f"{truth[0]},{truth[1]}", 0.0)
        for grid, truth in zip(beliefs, truth_path, strict=True)
    ]
    return OverlaySeries(
        role=detected,
        opponent=opponent,
        steps=steps,
        errors=errors,
        truth_path=truth_path,
        beliefs=beliefs,
    )


def _single_belief_role(events: list[dict[str, Any]]) -> str:
    """The unique belief-snapshot sender, or a loud refusal when ambiguous."""
    senders = {e["sender"] for e in events if e["event"] == "belief"}
    if len(senders) != 1:
        raise ValueError(
            f"cannot auto-detect the role: belief snapshots from {sorted(senders)} - pass one"
        )
    return str(senders.pop())

"""The audit-side scent-physics check (M6-7 rider; FR-11; PLAN §4; D2-approved).

Re-derives the trail the opponent's REVEALED (sealed, audited) positions imply
under the locked scent model and diffs it against the grids they actually
transmitted (our verbatim inbound archive). SQ3 stance unchanged: grids are
unauthenticated and never sealed, so a mismatch is EVIDENCE-GRADE ONLY — a loud
JSONL event for the dispute file; it never flips a result and never feeds the
belief (M3-8 boundary). Disclosed in KNOWN_LIMITATIONS as proving inconsistency
"only to us".
"""

from __future__ import annotations

from typing import Any

from copthief_core.domain.scent import ScentField
from copthief_core.shared.config_model import Constitution


def _revealed_positions(records: list[dict[str, Any]]) -> dict[int, tuple[int, int]]:
    """step -> revealed position, game records only; malformed entries skipped."""
    positions: dict[int, tuple[int, int]] = {}
    for record in records:
        payload = record.get("payload", {})
        step, position = payload.get("step"), payload.get("position")
        if isinstance(step, int) and step >= 1 and isinstance(position, list):
            positions.setdefault(step, (position[0], position[1]))
    return positions


def scent_physics_mismatches(
    *,
    records: list[dict[str, Any]],
    inbound: list[dict[str, Any]],
    constitution: Constitution,
) -> list[dict[str, Any]]:
    """Every step whose transmitted grid contradicts the revealed walk.

    Input: the opponent's revealed audit records + our archived inbound messages
    (wire dicts with `step`/`smell_grid`) + the signed constitution. Output: one
    entry per mismatching step `{step, cells}` (count of differing cells) —
    empty for an honest peer (the locked model is deterministic, round-3 exact).
    """
    positions = _revealed_positions(records)
    transmitted = {
        m["step"]: m["smell_grid"]
        for m in inbound
        if isinstance(m.get("step"), int) and isinstance(m.get("smell_grid"), dict)
    }
    pheromones = constitution.pheromones
    field = ScentField(
        board_size=constitution.board.grid_size,
        window=pheromones.grid_size,
        decay=pheromones.decay,
        min_center_intensity=pheromones.min_center_intensity,
        origin=constitution.board.axis_start_index,
    )
    mismatches: list[dict[str, Any]] = []
    for step in sorted(positions):
        field.deposit(positions[step], pheromones.center_intensity)
        field.decay()
        expected = field.snapshot()
        got = transmitted.get(step)
        if got is None:
            continue  # nothing archived for this step (pre-v1.1 log) — not evidence
        differing = {
            cell for cell in expected.keys() | got.keys() if expected.get(cell) != got.get(cell)
        }
        if differing:
            mismatches.append({"step": step, "cells": len(differing)})
    return mismatches


def emit_scent_physics(
    session: Any,  # noqa: ANN401 - PeerSession (no import cycle)
    theirs: dict[str, Any],
    emit: Any,  # noqa: ANN401 - LogFn
) -> None:
    """Settlement tail: run the check over a received audit and log the evidence."""
    their_records = theirs.get("records")
    if not isinstance(their_records, list):
        return
    mismatches = scent_physics_mismatches(
        records=their_records,
        inbound=[message.to_wire() for message in session.inbound],
        constitution=session.constitution,
    )
    if mismatches:
        emit(
            {
                "event": "scent_physics_mismatch",
                "sender": session.role,
                "payload": {"opponent": session.opponent_group, "mismatches": mismatches},
            }
        )

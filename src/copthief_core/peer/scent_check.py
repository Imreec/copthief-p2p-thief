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
from copthief_core.domain.scent_models import make_scent_model
from copthief_core.shared.config_model import Constitution, PrivateSettings
from copthief_core.shared.locked_models import SCENT_MODEL


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
    private: PrivateSettings,
    tolerance: float = 0.0,
) -> list[dict[str, Any]]:
    """Every step whose transmitted grid contradicts the revealed walk.

    Input: the opponent's revealed audit records + our archived inbound messages
    (wire dicts with `step`/`smell_grid`) + the signed constitution + the private
    settings (which name the locked model). Output: one entry per mismatching step
    `{step, cells}` (count of differing cells).

    Comparison mode follows the LOCKED MODEL (M3-8). Under the reference form the
    re-derivation is round-3 exact, so a difference of any size is a difference. Under
    `multiplicative_book_v1` nothing is rounded and each side RECOMPUTES rather than
    receives, so two honest peers legitimately differ in the last IEEE-754 bit on 75 of
    534 probed inputs — comparing byte-wise there would manufacture evidence against an
    honest opponent, so a model that does not round is compared within `tolerance`.
    """
    positions = _revealed_positions(records)
    transmitted = {
        m["step"]: m["smell_grid"]
        for m in inbound
        if isinstance(m.get("step"), int) and isinstance(m.get("smell_grid"), dict)
    }
    pheromones = constitution.pheromones
    doc = private.locked_models.doc(SCENT_MODEL, private.scent_model)
    model = make_scent_model(private.scent_model, params=doc["params"])
    field = ScentField(
        board_size=constitution.board.grid_size,
        origin=constitution.board.axis_start_index,
        model=model,
    )
    # NB `transmitted` is not consulted here. It describes the MODEL's own protocol,
    # while our wire shape carries a `smell_grid` regardless — so whatever the opponent
    # actually archived is what we can contradict. A peer that transmits nothing simply
    # has no grid at any step, and the `got is None` skip below reports no evidence
    # rather than a vacuous pass. Open item (PRD_scent §9.3, TODO M3-8): under
    # `multiplicative_book_v1` a peer honouring `transmitted: false` puts no grid on
    # the wire at all, leaving this check with nothing to check.
    slack = 0.0 if model.rounds else tolerance
    mismatches: list[dict[str, Any]] = []
    for step in sorted(positions):
        field.advance(positions[step], pheromones.center_intensity)
        expected = field.snapshot()
        got = transmitted.get(step)
        if got is None:
            continue  # nothing archived for this step (pre-v1.1 log) — not evidence
        differing = {
            cell
            for cell in expected.keys() | got.keys()
            if abs(expected.get(cell, 0.0) - got.get(cell, 0.0)) > slack
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
        private=session.private,
        tolerance=session.private.scent_physics_tolerance,
    )
    if mismatches:
        emit(
            {
                "event": "scent_physics_mismatch",
                "sender": session.role,
                "payload": {"opponent": session.opponent_group, "mismatches": mismatches},
            }
        )

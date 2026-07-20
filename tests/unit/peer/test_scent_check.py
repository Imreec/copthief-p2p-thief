"""M6-7 rider (FR-11, D2-approved): the audit-side scent-physics check.

SQ3 stance unchanged: transmitted grids are UNAUTHENTICATED and never sealed, so
a mismatch is evidence-grade only — a loud event, never a result change, never a
belief input (M3-8 boundary). Honest grids re-derive EXACTLY (the locked model is
deterministic, round-3); a fabricated grid diffs against the trail the revealed
(sealed, audited) moves imply.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from copthief_core.domain.scent import ScentField
from copthief_core.peer.scent_check import scent_physics_mismatches
from copthief_core.shared.config import load_all

CONSTITUTION, _SHIPPED, _LIMITS = load_all(Path("config"), counted=False)


def _honest_walk(positions: list[tuple[int, int]]) -> tuple[list[dict], list[dict]]:
    """Revealed records + the wire grids an HONEST peer would transmit for them."""
    field = ScentField(
        board_size=CONSTITUTION.board.grid_size,
        window=CONSTITUTION.pheromones.grid_size,
        decay=CONSTITUTION.pheromones.decay,
        min_center_intensity=CONSTITUTION.pheromones.min_center_intensity,
        origin=CONSTITUTION.board.axis_start_index,
    )
    records: list[dict[str, Any]] = []
    inbound: list[dict[str, Any]] = []
    for step, position in enumerate(positions, start=1):
        field.deposit(position, CONSTITUTION.pheromones.center_intensity)
        field.decay()
        records.append({"payload": {"step": step, "position": list(position)}})
        inbound.append({"step": step, "smell_grid": field.snapshot()})
    return records, inbound


def test_an_honest_trail_produces_zero_mismatches() -> None:
    records, inbound = _honest_walk([(3, 3), (4, 3), (4, 4)])
    assert (
        scent_physics_mismatches(records=records, inbound=inbound, constitution=CONSTITUTION) == []
    )


def test_a_fabricated_grid_is_flagged_at_its_step_with_cell_counts() -> None:
    records, inbound = _honest_walk([(3, 3), (4, 3), (4, 4)])
    inbound[1]["smell_grid"] = {"0,0": 0.9}  # a planted trail far from the walk
    mismatches = scent_physics_mismatches(
        records=records, inbound=inbound, constitution=CONSTITUTION
    )
    assert [m["step"] for m in mismatches] == [2]
    assert mismatches[0]["cells"] >= 1


def test_steps_without_a_transmitted_grid_are_skipped_not_flagged() -> None:
    records, inbound = _honest_walk([(3, 3), (4, 3)])
    del inbound[0]  # we never archived a message for step 1 (e.g. pre-v1.1 log)
    assert (
        scent_physics_mismatches(records=records, inbound=inbound, constitution=CONSTITUTION) == []
    )


def test_spec_and_malformed_records_never_crash_the_check() -> None:
    records, inbound = _honest_walk([(3, 3)])
    records.insert(0, {"payload": {"step": 0, "type": "system_spec"}})
    records.append({"payload": {"step": 9}})  # no position revealed
    assert (
        scent_physics_mismatches(records=records, inbound=inbound, constitution=CONSTITUTION) == []
    )

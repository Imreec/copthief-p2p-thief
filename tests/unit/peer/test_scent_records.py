"""M7-58: the coordinate arrives under the name ITS AUTHOR chose, not ours.

Split from `test_scent_check` at the 150-line rule, mirroring the module split.

Live finding (2026-08-09, after six cross-team series): the audit-side scent check had
never run against a single opponent. It read the cell under `position` — OUR spelling and
nobody else's. best2934 and uoh-sqak write `state`; anrbj666 seal a `state_digest` and no
cell at all. So it found nothing, compared nothing, and reported no problems, which is
indistinguishable from a clean trail. Two of the tests below would have PASSED against the
old code for exactly that reason, which is why the forged-grid case carries the weight.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from copthief_core.domain.scent import ScentField
from copthief_core.peer.scent_check import emit_scent_physics, scent_physics_mismatches
from copthief_core.shared.config import load_all

CONSTITUTION, PRIVATE, _LIMITS = load_all(Path("config"), counted=False)


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


def test_a_peer_that_names_the_coordinate_state_is_still_checked() -> None:
    """M7-58: the coordinate arrives under the name ITS AUTHOR chose, not ours.

    Live 2026-08-09: this check had never run against a single opponent. It looked the
    coordinate up under `position`, which is OUR field name — best2934 and uoh-sqak write
    `state`, and anrbj666 publish only a `state_digest`. Six audits reported "no problems"
    having compared zero steps, which is indistinguishable from a clean trail.
    """
    records, inbound = _honest_walk([(3, 3), (4, 3), (4, 4)])
    for record in records:  # rewrite the honest trail under the other league spelling
        record["payload"]["state"] = record["payload"].pop("position")
    assert (
        scent_physics_mismatches(
            records=records, inbound=inbound, constitution=CONSTITUTION, private=PRIVATE
        )
        == []
    )


def test_a_forged_grid_is_caught_under_the_state_spelling_too() -> None:
    """The point of reading `state` is to CATCH things, not merely to stay quiet."""
    records, inbound = _honest_walk([(3, 3), (4, 3), (4, 4)])
    for record in records:
        record["payload"]["state"] = record["payload"].pop("position")
    inbound[1]["smell_grid"] = dict(inbound[1]["smell_grid"], **{"0,0": 0.9})
    mismatches = scent_physics_mismatches(
        records=records, inbound=inbound, constitution=CONSTITUTION, private=PRIVATE
    )
    assert [m["step"] for m in mismatches] == [2]


def test_a_non_coordinate_state_field_is_ignored() -> None:
    """`state` means a coordinate to some peers and something else to others, so it is
    accepted only when it LOOKS like one — a two-integer pair. anrbj666 seal a
    `state_digest` and no position at all; that must stay unreadable rather than be
    coerced into a false comparison."""
    records, inbound = _honest_walk([(3, 3), (4, 3), (4, 4)])
    for record in records:
        record["payload"].pop("position")
        record["payload"]["state"] = "5f2a9c"  # a digest, not a cell
    assert (
        scent_physics_mismatches(
            records=records, inbound=inbound, constitution=CONSTITUTION, private=PRIVATE
        )
        == []
    )


class _Wire:
    """An inbound message stand-in: only `to_wire()` is consumed here."""

    def __init__(self, step: int, grid: dict[str, float]) -> None:
        self._wire = {"step": step, "smell_grid": grid}

    def to_wire(self) -> dict[str, Any]:
        return self._wire


class _Session:
    """The handful of attributes `emit_scent_physics` reads."""

    role = "police"
    opponent_group = "someone"
    constitution = CONSTITUTION
    private = PRIVATE
    scent_refusals: list[dict[str, Any]] = []

    def __init__(self, inbound: list[_Wire]) -> None:
        self.inbound = inbound


def test_a_check_that_could_not_run_says_so() -> None:
    """M7-58: silence must not mean both "clean" and "I had nothing to compare".

    An opponent who seals a digest and no cell (anrbj666) is unauditable on physics, and
    that is a permanent, correct answer — but it must be SAID. Six cross-team series
    reported no problems having compared zero steps.
    """
    events: list[dict[str, Any]] = []
    session = _Session([_Wire(1, {"3,3": 0.9}), _Wire(2, {"3,3": 0.8})])
    theirs = {"records": [{"payload": {"step": 1, "state_digest": "5f2a9c"}}]}
    emit_scent_physics(session, theirs, events.append)
    unavailable = [e for e in events if e["event"] == "scent_physics_unavailable"]
    assert len(unavailable) == 1
    assert unavailable[0]["payload"]["grids"] == 2
    assert [e for e in events if e["event"] == "scent_physics_mismatch"] == []


def test_a_readable_walk_emits_no_unavailable_event() -> None:
    """The signal fires on absence, never on a peer we CAN re-walk."""
    records, inbound = _honest_walk([(3, 3), (4, 3)])
    events: list[dict[str, Any]] = []
    emit_scent_physics(
        _Session([_Wire(m["step"], m["smell_grid"]) for m in inbound]),
        {"records": records},
        events.append,
    )
    assert [e for e in events if e["event"] == "scent_physics_unavailable"] == []

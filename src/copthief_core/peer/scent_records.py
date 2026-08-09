"""Reading revealed cells out of an opponent's audit records (M7-58).

Split from `peer/scent_check` at the 150-line rule. The concern is genuinely separate:
the check knows the PHYSICS, this module knows how other implementations SPELL a board
cell — and the league spells it three ways.

Live finding (2026-08-09, after six cross-team series): the audit-side scent check had
never run against a single opponent. It looked the coordinate up under `position`, which
is OUR field name and nobody else's — best2934 and uoh-sqak write `state`, and anrbj666
publish a `state_digest` with no coordinate at all. It therefore found no positions,
compared nothing, and reported no problems, which reads exactly like a clean trail.
"""

from __future__ import annotations

from typing import Any

# Our own spelling first: our records carry BOTH `position` and `state`, and only
# `position` is guaranteed to be the cell.
POSITION_KEYS = ("position", "state")


def as_cell(value: Any) -> tuple[int, int] | None:  # noqa: ANN401 - arbitrary wire value
    """A wire value read as a board cell (Input: any decoded JSON value; Output: the cell
    or None).

    `state` means a coordinate to some peers and a digest to others, so the SHAPE is the
    admission test rather than the name: exactly two integers. `bool` is excluded because
    it is an `int` in Python and `[True, False]` is not a cell. Anything looser would
    manufacture a comparison against a peer that never revealed a position at all.
    """
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    row, col = value
    if isinstance(row, bool) or isinstance(col, bool):
        return None
    if not isinstance(row, int) or not isinstance(col, int):
        return None
    return (row, col)


def revealed_positions(records: list[dict[str, Any]]) -> dict[int, tuple[int, int]]:
    """step -> revealed cell for GAME records only (Input: the opponent's disclosed
    records; Output: the walk we can re-derive). Malformed entries are skipped, and a
    record that reveals no cell contributes nothing rather than a guess.
    """
    positions: dict[int, tuple[int, int]] = {}
    for record in records:
        payload = record.get("payload", {})
        step = payload.get("step")
        if not isinstance(step, int) or isinstance(step, bool) or step < 1:
            continue
        for key in POSITION_KEYS:
            cell = as_cell(payload.get(key))
            if cell is not None:
                positions.setdefault(step, cell)
                break
    return positions

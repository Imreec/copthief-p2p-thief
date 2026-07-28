"""In-play frame validity check (PRD_scent §10; M7-23; kit physics unchanged).

Across two CONSECUTIVE frames from one sender, the locked physics cancels the whole
history: the current frame must equal one `advance` of the previous frame for SOME
emitter cell. Zero explaining cells ⇒ the pair cannot both have come from a peer
playing by the rules (stale, malformed, or forged) — detectable at arrival, with no
knowledge of the opponent's position. Adopted from the opponent team's 2026-07-27
memo after independent verification (224/224 unique inversions, both models).

FIREWALL (§10.1, load-bearing): the same scan that validates also localizes. This
module therefore exposes a VERDICT ONLY — the matched candidate never leaves
`frame_explained`, is never logged, and never reaches belief or a brain. That is the
`info_mode: belief` posture offered to the opponent team, binding our own code first.

Pure — no I/O, no clock, no config reads; every quantitative value arrives as an
argument (constraint #5).
"""

from __future__ import annotations

from copthief_core.domain.scent_models import ScentModel
from copthief_core.domain.scent_types import Cells

__all__ = ["frame_explained"]


def _parse(grid: dict[str, float]) -> Cells:
    """Wire `"r,c"` keys to coordinate cells (values already wire-validated)."""
    cells: Cells = {}
    for key, value in grid.items():
        row, col = (int(part) for part in key.split(","))
        cells[(row, col)] = float(value)
    return cells


def _matches(predicted: Cells, observed: Cells, slack: float) -> bool:
    """Whole-field comparison; a missing key reads 0.0 (snapshots drop zero cells)."""
    return all(
        abs(predicted.get(cell, 0.0) - observed.get(cell, 0.0)) <= slack
        for cell in predicted.keys() | observed.keys()
    )


def frame_explained(
    prev: dict[str, float],
    now: dict[str, float],
    *,
    model: ScentModel,
    board_size: int,
    origin: int,
    intensity: float,
    tolerance: float,
) -> bool:
    """Whether SOME emitter cell explains `now` as one advance of `prev`.

    Input: the previous ACCEPTED wire grid (empty for step 1 — the locked docs pin
    `initial_field: "empty"`, so even the first frame is checkable), the arriving
    grid, the locked model, the board bounds, the signed emission intensity, and the
    audit slack. Output: True (accept) or False (refuse the whole frame). The compare
    mode follows M6-7's dispatch: a rounding model is compared exactly, a model that
    does not round within `tolerance` (the 75-of-534 last-bit finding, ADR-0004 v2).

    Every board cell is scanned — BARRIER CELLS INCLUDED: a cop that walls its own
    cell still emits from there that turn, so excluding walls rejects honest frames.
    """
    low, high = origin, origin + board_size

    def in_bounds(cell: tuple[int, int]) -> bool:
        return low <= cell[0] < high and low <= cell[1] < high

    observed = _parse(now)
    base = _parse(prev)
    slack = 0.0 if model.rounds else tolerance
    for row in range(low, high):
        for col in range(low, high):
            predicted = dict(base)
            model.advance(predicted, (row, col), intensity, in_bounds)
            if _matches(predicted, observed, slack):
                return True
    return False

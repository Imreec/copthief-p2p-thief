"""Scent observation scorers for the belief filter (PRD_belief §3; M7-14).

Two observation models, dispatched by what a scent value MEANS under the selected
physics (`ScentModel.spatial_kernel`):

- **Age vouchers** (reference form): linear decay makes intensity an AGE — each cell
  vouches for the opponent within `age` moves, weight spread over the Manhattan ball.
  Unchanged from M3-3 (98% argmax hit-rate); every shipped-model measurement stands.
- **Kernel match** (book form): the additive-clamped field makes intensity useless as
  age (a fresh ring-1 cell inverts to "age 4" — the M3-8 finding), but the kernel is a
  spatial template: score each hypothesis by how well the observed neighbourhood
  matches a fresh kernel centred there. `sum(min)/sum(max)` over the window rewards
  the true ring structure and penalizes both missing scent and the FLAT ceiling blobs
  a camper pins (the g02 capture signature) — excess intensity is mismatch, not youth.

Pure functions — no filter state, no I/O; the filter owns priors and normalization.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from copthief_core.domain.board import Board, Coord

if TYPE_CHECKING:
    from copthief_core.domain.scent_models import ScentModel

Kernel = list[tuple[float, ...]]


def parse_grid(grid: dict[str, float]) -> dict[Coord, float]:
    """Wire-form `"r,c" -> value` to coordinates, positive values only."""
    cells: dict[Coord, float] = {}
    for key, value in grid.items():
        if value > 0.0:
            row, col = (int(part) for part in key.split(","))
            cells[(row, col)] = value
    return cells


def age_voucher_scores(
    grid: dict[str, float], support: list[Coord], age_of: Callable[[float], int]
) -> dict[Coord, float]:
    """The M3-3 voucher heuristic: strongest `value / ball_size` voucher per cell."""
    vouchers = []
    for cell, value in parse_grid(grid).items():
        age = age_of(value)
        ball_size = 2 * age * age + 2 * age + 1  # Manhattan ball, boundary-blind
        vouchers.append((cell, value / ball_size, age))
    if not vouchers:
        return {}
    return {
        cell: max(
            (
                weight
                for (src, weight, age) in vouchers
                if abs(cell[0] - src[0]) + abs(cell[1] - src[1]) <= age
            ),
            default=0.0,
        )
        for cell in support
    }


def fresh_peak_scores(
    grid: dict[str, float], support: list[Coord], age_of: Callable[[float], int]
) -> dict[Coord, float]:
    """The sharp tier (M9-2): the unique age-zero stamp names the emitter cell.

    Under the subtractive form only a centre laid THIS turn can read `fresh_center`
    (rings are lower, older centres have decayed a step), so exactly one age-zero
    cell is the opponent's current cell. Anything else — no stamp (stale frame) or
    several (a field legal physics cannot produce) — abstains to `{}` and the caller
    falls back to the voucher path. Score 1.0 at the peak, 0.0 elsewhere; the FILTER
    owns how hard to trust it (SQ3: multiply, never eliminate).
    """
    peaks = [cell for cell, value in parse_grid(grid).items() if age_of(value) == 0]
    if len(peaks) != 1:
        return {}
    return {cell: 1.0 if cell == peaks[0] else 0.0 for cell in support}


def kernel_match_score(
    observed: dict[Coord, float], hypothesis: Coord, kernel: Kernel, board: Board
) -> float:
    """How well the observed field around `hypothesis` matches a fresh kernel there.

    `sum(min(obs, k)) / sum(max(obs, k))` over the in-bounds kernel window — 1.0 for
    an exact fresh kernel, lower for missing scent AND for flat saturation (excess is
    mismatch). Off-board window cells are skipped: the emission never reached them.
    """
    half = len(kernel) // 2
    matched = 0.0
    combined = 0.0
    for d_row in range(-half, half + 1):
        for d_col in range(-half, half + 1):
            cell = (hypothesis[0] + d_row, hypothesis[1] + d_col)
            if not board.in_bounds(cell):
                continue
            expected = kernel[half + d_row][half + d_col]
            actual = observed.get(cell, 0.0)
            matched += min(actual, expected)
            combined += max(actual, expected)
    return matched / combined if combined > 0.0 else 0.0


def innovation(
    observed: dict[Coord, float],
    previous: dict[Coord, float] | None,
    decayed: Callable[[float], float],
) -> dict[Coord, float]:
    """The fresh part of an observed field: observed minus the decay-predicted
    carry-over of the PREVIOUS observation (M7-14).

    Under the book model a lingering opponent saturates its whole window flat at the
    ceiling, so the raw field carries no kernel shape at all — but the innovation is
    (up to clamping) exactly one fresh kernel at the current cell, because the filter
    knows the model's decay and can subtract everything the past explains. With no
    previous observation the whole field is the innovation.
    """
    residual: dict[Coord, float] = {}
    for cell, value in observed.items():
        carry = decayed(previous.get(cell, 0.0)) if previous is not None else 0.0
        fresh = value - carry
        if fresh > 0.0:
            residual[cell] = fresh
    return residual


def kernel_match_scores(
    observed: dict[Coord, float], support: list[Coord], kernel: Kernel, board: Board
) -> dict[Coord, float]:
    """`kernel_match_score` per support cell over one parsed (or residual) field."""
    return {cell: kernel_match_score(observed, cell, kernel, board) for cell in support}


def observation_scores(
    grid: dict[str, float],
    support: list[Coord],
    scent: ScentModel,
    last_scent: dict[Coord, float] | None,
    board: Board,
    smell_trust: float,
    fresh_peak_trust: float,
) -> tuple[dict[Coord, float], float, dict[Coord, float] | None]:
    """One observed field to (scores, trust, next_last_scent) — the filter's whole
    scent dispatch (moved here at M9-2, 150-line rule): kernel shape-match for
    spatial models, else the sharp fresh-peak decode when enabled (abstention
    falls back to the voucher). The filter owns priors and normalization."""
    kernel = scent.spatial_kernel()
    if kernel is not None:
        # Shape-match the INNOVATION: what the decay-predicted past cannot
        # explain is (up to clamping) one fresh kernel at the current cell.
        observed = parse_grid(grid)
        residual = innovation(observed, last_scent, scent.decayed)
        return kernel_match_scores(residual, support, kernel, board), smell_trust, observed
    if fresh_peak_trust > 0.0:  # M9-2: the sharp decode outranks the voucher
        scores = fresh_peak_scores(grid, support, scent.age_of)
        if scores:
            return scores, fresh_peak_trust, last_scent
    return age_voucher_scores(grid, support, scent.age_of), smell_trust, last_scent

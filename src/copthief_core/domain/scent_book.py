"""The book's ch.4 scent model — `multiplicative_book_v1` (kit SPEC §5.1, PROMOTED).

Its own module because the two registrations together exceed the 150-line rule, and
because this one is the DEVIATION: it plays only under an explicit pair-lock, while
`subtractive_chebyshev_v1` next door is what every unlocked game still runs.

Pure: no I/O, no clock, no config reads. The kernel and every constant arrive from the
locked-model registry (`config/locked_models.json`), never from source (CLAUDE.md §1 #5).
"""

from __future__ import annotations

from math import log
from typing import Any

from copthief_core.domain.board import Coord
from copthief_core.domain.scent_types import Cells, InBounds


class MultiplicativeBookV1:
    """The book's ch.4 model: `tau' = clamp((1 - rho) * tau + kernel_delta, 0, center)`.

    No rounding anywhere, so the evaluation order is load-bearing: `(1-rho)*tau + delta`
    and `tau - rho*tau + delta` differ in the last IEEE-754 bit on 75 of 534 probed inputs
    (ADR-0004 v2). The pinned form is the one below, and the kit's `ordering_probe` vectors
    hold it there. The upper clamp is not in the book's printed `max(0, .)` — it comes from
    the book's separate declaration that tau is continuous in [0, 0.9] (PRD_scent §9.2).
    """

    name = "multiplicative_book_v1"
    receiver_side_decay = False  # each side RECOMPUTES the rival's field; none is received
    transmitted = False
    # No rounding, and each side RECOMPUTES rather than receives, so two honest peers
    # differ in the last IEEE-754 bit on ~14% of inputs. Byte-wise comparison would
    # manufacture evidence against an honest opponent (ADR-0004 v2).
    rounds = False

    def __init__(self, params: dict[str, Any]) -> None:
        self.window = int(params["field_size"])
        self._half = self.window // 2
        self._rho = float(params["decay_rho"])
        self.center_intensity = float(params["center_intensity"])
        self.kernel = [tuple(float(v) for v in row) for row in params["kernel"]]
        low, high = params["clamp"]
        self._low, self._high = float(low), float(high)

    def step_cell(self, tau: float, delta: float) -> float:
        """One cell, one full turn. The pinned evaluation order, expressed once."""
        return min(max((1.0 - self._rho) * tau + delta, self._low), self._high)

    def _delta_at(self, center: Coord, cell: Coord) -> float:
        d_row, d_col = cell[0] - center[0], cell[1] - center[1]
        if abs(d_row) > self._half or abs(d_col) > self._half:
            return 0.0
        return self.kernel[self._half + d_row][self._half + d_col]

    def _window(self, center: Coord, ok: InBounds) -> list[Coord]:
        span = range(-self._half, self._half + 1)
        return [
            cell
            for d_row in span
            for d_col in span
            if ok(cell := (center[0] + d_row, center[1] + d_col))
        ]

    def deposit(self, cells: Cells, center: Coord, intensity: float, ok: InBounds) -> None:
        """Additive kernel, upper-clamped. `intensity` is unused: the book's delta IS the
        kernel, an absolute table, unconditioned by any emission strength or minimum."""
        for cell in self._window(center, ok):
            value = min(cells.get(cell, 0.0) + self._delta_at(center, cell), self._high)
            if value > 0.0:
                cells[cell] = value

    def decay(self, cells: Cells) -> None:
        for cell, value in list(cells.items()):
            cells[cell] = self.step_cell(value, 0.0)

    def fresh_center(self) -> float:
        """A just-laid centre reads the kernel centre: decay of an empty cell, then Delta."""
        return self.center_intensity

    def age_of(self, value: float) -> int:
        """LOGARITHMIC inversion — the reason the filter cannot hard-code the reference
        shape: under `tau*(1-rho)^age` a subtractive age estimate is simply wrong."""
        if value <= 0.0 or not 0.0 < self._rho < 1.0:
            return 0
        return max(0, round(log(value / self.center_intensity) / log(1.0 - self._rho)))

    def advance(self, cells: Cells, center: Coord, intensity: float, ok: InBounds) -> None:
        """Decay and deposit as ONE expression per cell — the order the kit pins."""
        for cell in set(cells) | set(self._window(center, ok)):
            value = self.step_cell(cells.get(cell, 0.0), self._delta_at(center, cell))
            if value > 0.0 or cell in cells:
                cells[cell] = value

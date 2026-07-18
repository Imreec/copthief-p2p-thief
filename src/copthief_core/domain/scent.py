"""Scent field (book ch.4; kit SPEC §5 pins the byte-level form; ADR-0004).

Re-derived from the kit's pinned construction — radial Chebyshev emission with
`falloff = intensity / (half + 1)`, SUBTRACTIVE per-step decay (the book's prose says
multiplicative; the release's own reference implements subtractive and the kit pins
that choice — ADR-0004), round-3 everywhere, and the sparse `{"r,c": value}` wire form.
Each peer holds two instances (PRD_scent §3): `own_trail` (we deposit; only its snapshot
crosses the wire) and `known_field` (absorbs what the opponent transmits; feeds belief).
Pure — no I/O, no clock, no config reads; all quantitative values arrive as arguments.
"""

from __future__ import annotations

from copthief_core.domain.board import Coord

# Round-3 is part of the kit-pinned construction (like the commit's pipe separator),
# not a tunable — a different precision transmits different bytes.
_ROUND_DIGITS = 3


def locked_model_document(
    *, center_intensity: float, decay: float, grid_size: int, min_center_intensity: float
) -> dict[str, object]:
    """The handshake artifact (PRD_scent §4): formula name + params + numeric example.

    Both peers hash this with the standard canonical form and exchange it at handshake,
    so a scent-model dispute is diagnosable to a hash. The example is per-ring: what a
    fresh deposit stores, and what it transmits after the one SQ1 decay.
    """
    half = grid_size // 2
    falloff = center_intensity / (half + 1)
    deposited = [
        round(max(0.0, center_intensity - falloff * ring), _ROUND_DIGITS)
        for ring in range(half + 1)
    ]
    transmitted = [round(max(0.0, value - decay), _ROUND_DIGITS) for value in deposited]
    return {
        "formula": "subtractive_chebyshev_v1",
        "params": {
            "pheromone_center_intensity": center_intensity,
            "pheromone_decay": decay,
            "pheromone_grid_size": grid_size,
            "pheromone_min_center_intensity": min_center_intensity,
        },
        "example": {"deposited_by_ring": deposited, "transmitted_by_ring": transmitted},
    }


class ScentEmissionError(ValueError):
    """A deposit below the signed `pheromone_min_center_intensity` gate (hard error)."""


class ScentField:
    """One peer-side scent field: emission window math + decay + wire snapshot/absorb.

    Input: board side + emission window side + per-step decay + emission gate (+ the
    board's axis start index); Output: pure field queries and the wire forms.
    """

    def __init__(
        self,
        *,
        board_size: int,
        window: int,
        decay: float,
        min_center_intensity: float,
        origin: int = 0,
    ) -> None:
        self._low = origin
        self._high = origin + board_size
        self._half = window // 2
        self._decay = decay
        self._min_center = min_center_intensity
        self._cells: dict[Coord, float] = {}

    def _in_bounds(self, cell: Coord) -> bool:
        return self._low <= cell[0] < self._high and self._low <= cell[1] < self._high

    def deposit(self, center: Coord, intensity: float) -> None:
        """Radially emit `intensity` at `center` over the window, max-merged into the
        field; off-board cells are clipped. Raises ScentEmissionError below the gate."""
        if intensity < self._min_center:
            raise ScentEmissionError(
                f"deposit {intensity} below min_center_intensity {self._min_center}"
            )
        falloff = intensity / (self._half + 1)
        for d_row in range(-self._half, self._half + 1):
            for d_col in range(-self._half, self._half + 1):
                cell = (center[0] + d_row, center[1] + d_col)
                if not self._in_bounds(cell):
                    continue
                ring = max(abs(d_row), abs(d_col))
                value = round(max(0.0, intensity - falloff * ring), _ROUND_DIGITS)
                if value > 0.0:
                    self._cells[cell] = max(self._cells.get(cell, 0.0), value)

    def decay(self) -> None:
        """One game-step subtractive decay over every known cell, clamped at 0.

        Cells stay known at 0.0 (the kit decay vectors pin the retained key) — only
        `snapshot()` filters them from the wire form.
        """
        self._cells = {
            cell: round(max(0.0, value - self._decay), _ROUND_DIGITS)
            for cell, value in self._cells.items()
        }

    def absorb(self, grid: dict[str, float]) -> None:
        """Max-merge a received wire snapshot; off-board keys are ignored (the wire
        layer has already validated the `"r,c"` key shape — PRD_scent §3)."""
        for key, value in grid.items():
            row, col = (int(part) for part in key.split(","))
            if self._in_bounds((row, col)):
                self._cells[(row, col)] = max(self._cells.get((row, col), 0.0), value)

    def snapshot(self) -> dict[str, float]:
        """The wire form (kit §5): strictly-positive cells only, `"r,c"` string keys."""
        return {f"{cell[0]},{cell[1]}": value for cell, value in self._cells.items() if value > 0.0}

    def cells(self) -> dict[Coord, float]:
        """Every known cell (including decayed-to-zero ones) — belief/test read surface."""
        return dict(self._cells)

    def intensity_at(self, cell: Coord) -> float:
        """The field value at `cell` (0.0 when unknown)."""
        return self._cells.get(cell, 0.0)

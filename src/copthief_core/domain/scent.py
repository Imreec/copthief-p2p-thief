"""Scent field (book ch.4; kit SPEC §5 pins the byte-level form; ADR-0004).

The field owns the board bounds and the cell store; the PHYSICS lives in a named
`ScentModel` (`domain/scent_models`, ADR-0004 v2). Constructed without one, the field
builds `subtractive_chebyshev_v1` from its own arguments — the reference form, our
default, byte-identical to what M3-2 shipped (the book's prose says multiplicative; the
release's own reference implements subtractive and the kit pins that choice — ADR-0004).

Each peer holds two instances (PRD_scent §3): `own_trail` (we deposit; only its snapshot
crosses the wire, and only for a model whose `transmitted` is true) and `known_field`
(absorbs what the opponent transmits; feeds belief).

Pure — no I/O, no clock, no config reads; all quantitative values arrive as arguments.
"""

from __future__ import annotations

from copthief_core.domain.board import Coord
from copthief_core.domain.scent_models import ScentModel, SubtractiveChebyshevV1

# Round-3 is part of the kit-pinned reference construction (like the commit's pipe
# separator), not a tunable — a different precision transmits different bytes.
_ROUND_DIGITS = 3


class ScentEmissionError(ValueError):
    """A deposit below the signed `pheromone_min_center_intensity` gate (hard error)."""


class ScentField:
    """One peer-side scent field: board bounds + cell store, physics delegated to a model.

    Input: board side, plus EITHER a named model OR the default model's parameters
    (emission window side, per-step decay, emission gate); Output: pure field queries and
    the wire forms.
    """

    def __init__(
        self,
        *,
        board_size: int,
        window: int | None = None,
        decay: float | None = None,
        min_center_intensity: float | None = None,
        emit_intensity: float | None = None,
        origin: int = 0,
        model: ScentModel | None = None,
    ) -> None:
        self._low = origin
        self._high = origin + board_size
        self._cells: dict[Coord, float] = {}
        if model is None:
            model = SubtractiveChebyshevV1(
                {
                    "field_size": window,
                    # The signed emission strength. It never affects `deposit` (which
                    # takes the intensity per call) but it IS the belief filter's
                    # age-zero anchor, so a field built without it would hand the
                    # observation model a fresh-centre of `-decay` (M3-8 regression,
                    # caught by the M3-3 per-seed pin).
                    "emit_intensity": emit_intensity,
                    "decay_per_step": decay,
                    "min_center_intensity": min_center_intensity,
                    "rounding_decimals": _ROUND_DIGITS,
                }
            )
        self.model = model

    @property
    def transmitted(self) -> bool:
        """Whether this model's field crosses the wire at all (kit SPEC §7 `transmitted`)."""
        return self.model.transmitted

    @property
    def receiver_side_decay(self) -> bool:
        """Whether a RECEIVED field decays on receipt — true for the reference form, false
        for the book model, which is recomputed rather than received (PRD_scent §9.2)."""
        return self.model.receiver_side_decay

    def _in_bounds(self, cell: Coord) -> bool:
        return self._low <= cell[0] < self._high and self._low <= cell[1] < self._high

    def deposit(self, center: Coord, intensity: float | None = None) -> None:
        """Emit at `center` per the model, max-merged or added into the field; off-board
        cells are clipped. Raises ScentEmissionError below the model's emission gate."""
        intensity = self._gate(intensity)
        self.model.deposit(self._cells, center, intensity, self._in_bounds)

    def decay(self) -> None:
        """One decay pass over every known cell, per the model.

        Cells stay known at 0.0 under the reference form (the kit decay vectors pin the
        retained key) — only `snapshot()` filters them from the wire form.
        """
        self.model.decay(self._cells)

    def advance(self, center: Coord, intensity: float | None = None) -> None:
        """One full turn of this trail — emission and decay in the model's own order.

        This is the cadence primitive (PRD_scent §9.3): the reference form deposits then
        decays, the book model does both in one clamped expression.
        """
        intensity = self._gate(intensity)
        self.model.advance(self._cells, center, intensity, self._in_bounds)

    def _gate(self, intensity: float | None) -> float:
        """The signed `min_center_intensity` emission gate — a reference term, inert under
        the book model, whose delta is the kernel unconditioned by any minimum (§9.1)."""
        minimum = getattr(self.model, "min_center_intensity", None)
        if intensity is None:
            intensity = getattr(self.model, "emit_intensity", 0.0)
        if minimum is not None and intensity < minimum:
            raise ScentEmissionError(f"deposit {intensity} below min_center_intensity {minimum}")
        return intensity

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

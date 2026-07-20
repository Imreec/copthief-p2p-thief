"""Named scent models (ADR-0004 v2; kit SPEC §5 / §5.1 / §7).

Two registrations, one protocol. `subtractive_chebyshev_v1` is the reference form and
**our default** — unchanged from M3-2, byte-identical on the wire. `multiplicative_book_v1`
is the book's ch.4 model, playable only under a pair-lock (PRD_scent §9).

Three primitives, because the field needs all three and the two models disagree about how
they compose: `deposit` (emission alone), `decay` (one decay pass alone — the receiver-side
pass runs for one model and not the other), and `advance` (the full-turn own-trail update,
which is where each model's ORDER lives — deposit-then-decay versus decay-then-deposit).

Pure: no I/O, no clock, no config reads. Every quantitative value arrives from the locked
model registry (`config/locked_models.json`), never from source (CLAUDE.md §1 #5).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from copthief_core.domain.board import Coord
from copthief_core.domain.scent_book import MultiplicativeBookV1
from copthief_core.domain.scent_types import Cells, InBounds


class ScentModelError(ValueError):
    """An unregistered model name, or params that do not match the registration."""


class ScentModel(Protocol):
    """The physics of one named registration (kit SPEC §7 `params`)."""

    name: str
    window: int
    receiver_side_decay: bool
    transmitted: bool
    rounds: bool  # whether the model quantizes — decides byte-wise vs tolerant compare

    def deposit(self, cells: Cells, center: Coord, intensity: float, ok: InBounds) -> None:
        """Emit at `center` into `cells`, clipped to the board."""

    def decay(self, cells: Cells) -> None:
        """One decay pass over every known cell."""

    def advance(self, cells: Cells, center: Coord, intensity: float, ok: InBounds) -> None:
        """One full turn of an own trail: emission and decay, in THIS model's order."""

    def fresh_center(self) -> float:
        """The value a just-laid centre reads — the belief filter's age-zero anchor."""

    def age_of(self, value: float) -> int:
        """Turns since deposit, inverted from `value` under THIS model's falloff.

        The observation model the exact-Bayes filter needs (PRD_belief §3): a cell
        vouches for the opponent having been within `age` moves of it.
        """


class SubtractiveChebyshevV1:
    """The reference form (kit SPEC §5): radial Chebyshev rings, linear falloff, round-3.

    Emission max-merges; decay is `v - decay_per_step` clamped at 0. Cells stay known at
    0.0 — the kit decay vectors pin the retained key; only the wire snapshot filters them.
    """

    name = "subtractive_chebyshev_v1"
    receiver_side_decay = True
    transmitted = True
    rounds = True  # round-3 quantizes every value, so the audit compares byte-wise

    def __init__(self, params: dict[str, Any]) -> None:
        self.window = int(params["field_size"])
        self._half = self.window // 2
        # Emission strength: `deposit` takes it per call, but `fresh_center` — the
        # belief filter's age-zero anchor — needs the signed value.
        self.emit_intensity = float(params.get("emit_intensity") or 0.0)
        self.min_center_intensity = float(params["min_center_intensity"])
        self._decay = float(params["decay_per_step"])
        self._digits = int(params["rounding_decimals"])

    def deposit(self, cells: Cells, center: Coord, intensity: float, ok: InBounds) -> None:
        falloff = intensity / (self._half + 1)
        for d_row in range(-self._half, self._half + 1):
            for d_col in range(-self._half, self._half + 1):
                cell = (center[0] + d_row, center[1] + d_col)
                if not ok(cell):
                    continue
                ring = max(abs(d_row), abs(d_col))
                value = round(max(0.0, intensity - falloff * ring), self._digits)
                if value > 0.0:
                    cells[cell] = max(cells.get(cell, 0.0), value)

    def decay(self, cells: Cells) -> None:
        for cell, value in list(cells.items()):
            cells[cell] = round(max(0.0, value - self._decay), self._digits)

    def advance(self, cells: Cells, center: Coord, intensity: float, ok: InBounds) -> None:
        """Deposit, THEN decay — the SQ1 timing pinned live at Stage A (PRD_scent §2)."""
        self.deposit(cells, center, intensity, ok)
        self.decay(cells)

    def fresh_center(self) -> float:
        """A just-laid centre transmits at `emit_intensity - decay` (PRD_scent §2)."""
        return round(self.emit_intensity - self._decay, self._digits)

    def age_of(self, value: float) -> int:
        """LINEAR inversion: every missing `decay` of intensity is one turn older."""
        if not self._decay:
            return 0
        return max(0, round((self.fresh_center() - value) / self._decay))


_MODELS: dict[str, Callable[[dict[str, Any]], ScentModel]] = {
    SubtractiveChebyshevV1.name: SubtractiveChebyshevV1,
    MultiplicativeBookV1.name: MultiplicativeBookV1,
}


def make_scent_model(name: str, *, params: dict[str, Any]) -> ScentModel:
    """Build a registered model from its locked-registry `params` block.

    Input: a registered name + the `params` of its locked-model doc; Output: the model.
    An unknown name is a hard error — a lock we cannot play is not a lock we may declare.
    """
    if name not in _MODELS:
        raise ScentModelError(f"unregistered scent model {name!r}; known: {sorted(_MODELS)}")
    return _MODELS[name](params)

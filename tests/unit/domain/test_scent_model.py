"""Named scent models (ADR-0004 v2): selection, per-model flags, and ORDER.

The kit vectors (tests/conformance) pin the numbers; this file pins the behaviour the
numbers cannot show — that the two models compose their primitives differently, that the
receiver-side pass runs for one and not the other, and that the default is untouched.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from copthief_core.domain.scent import ScentEmissionError, ScentField
from copthief_core.domain.scent_models import (
    ScentModelError,
    make_scent_model,
)

REGISTRY = json.loads(Path("config/locked_models.json").read_text(encoding="utf-8"))["models"]


def _params(name: str) -> dict[str, Any]:
    return REGISTRY[f"scent_model:{name}"]["params"]


def _field(name: str, board_size: int = 7) -> ScentField:
    return ScentField(board_size=board_size, model=make_scent_model(name, params=_params(name)))


def test_the_default_model_is_the_reference_form() -> None:
    field = _field("subtractive_chebyshev_v1")
    assert field.model.name == "subtractive_chebyshev_v1"
    assert field.transmitted is True
    assert field.receiver_side_decay is True


def test_the_book_model_neither_transmits_nor_decays_on_receipt() -> None:
    """It is RECOMPUTED from revealed actions, so there is no received copy to decay."""
    field = _field("multiplicative_book_v1")
    assert field.transmitted is False
    assert field.receiver_side_decay is False


def test_an_unregistered_name_is_a_hard_error() -> None:
    with pytest.raises(ScentModelError, match="unregistered scent model"):
        make_scent_model("gaussian_fitted_v9", params={})


def test_advance_orders_deposit_and_decay_per_model() -> None:
    """The reference form deposits THEN decays; the book model does both at once, so a
    fresh centre reads center-decay for one and the full kernel centre for the other."""
    reference = _field("subtractive_chebyshev_v1")
    reference.advance((3, 3), 0.9)
    assert reference.intensity_at((3, 3)) == 0.8  # 0.9 deposited, then one decay

    book = _field("multiplicative_book_v1")
    book.advance((3, 3))
    assert book.intensity_at((3, 3)) == 0.9  # decay of an empty cell, then the kernel


def test_advance_reproduces_the_legacy_deposit_then_decay_pair_exactly() -> None:
    """The cadence primitive must be byte-identical to the two calls it replaces."""
    stepwise = _field("subtractive_chebyshev_v1")
    stepwise.deposit((2, 4), 0.9)
    stepwise.decay()
    combined = _field("subtractive_chebyshev_v1")
    combined.advance((2, 4), 0.9)
    assert combined.cells() == stepwise.cells()


def test_the_emission_gate_binds_the_reference_form_only() -> None:
    """`min_center_intensity` is a reference term, inert under the book model (§9.1)."""
    with pytest.raises(ScentEmissionError, match="below min_center_intensity"):
        _field("subtractive_chebyshev_v1").deposit((3, 3), 0.4)
    book = _field("multiplicative_book_v1")
    book.deposit((3, 3), 0.4)  # no gate: the book's delta IS the kernel
    assert book.intensity_at((3, 3)) == 0.9


def test_the_book_model_clamps_above_at_center_intensity() -> None:
    """Without the upper clamp a saturated cell reaches 0.9*0.9 + 0.62 = 1.43, outside
    the book's own stated [0, 0.9] range for tau (PRD_scent §9.2)."""
    model = make_scent_model("multiplicative_book_v1", params=_params("multiplicative_book_v1"))
    assert model.step_cell(0.9, 0.62) == 0.9


def test_the_book_model_never_rounds() -> None:
    """Rounding would hide the last-bit divergence the kit's ordering probe pins."""
    model = make_scent_model("multiplicative_book_v1", params=_params("multiplicative_book_v1"))
    assert model.step_cell(0.62, 0.2) == 0.758
    assert model.step_cell(0.758, 0.2) == 0.8822000000000001


def test_a_field_built_without_a_model_is_the_shipped_default() -> None:
    """The M3-2 constructor still works and still plays the reference form untouched."""
    legacy = ScentField(board_size=7, window=5, decay=0.1, min_center_intensity=0.5)
    named = _field("subtractive_chebyshev_v1")
    legacy.deposit((3, 3), 0.9)
    named.deposit((3, 3), 0.9)
    assert legacy.snapshot() == named.snapshot()

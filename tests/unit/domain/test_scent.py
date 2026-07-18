"""domain/scent unit suite (PRD_scent §7): emission, gate, decay, merge, wire forms.

The kit vectors (tests/conformance) pin the byte-level math; these tests pin the
behaviors around it — the emission gate, max-merge, the SQ1 deposit-then-decay order,
and the bounds/robustness edges the vectors do not exercise.
"""

import pytest

from copthief_core.domain.scent import ScentEmissionError, ScentField

# Shipped-config values (game.json `pheromones`), restated here as test inputs only.
CENTER, DECAY, WINDOW, MIN_CENTER = 0.9, 0.1, 5, 0.5


def make_field(*, board_size: int = 7, origin: int = 0) -> ScentField:
    return ScentField(
        board_size=board_size,
        window=WINDOW,
        decay=DECAY,
        min_center_intensity=MIN_CENTER,
        origin=origin,
    )


def test_falloff_derives_from_window_size() -> None:
    # window 5 -> half 2 -> falloff I/3: ring values I, 2I/3, I/3 (round-3).
    field = make_field()
    field.deposit((3, 3), CENTER)
    assert field.intensity_at((3, 3)) == 0.9
    assert field.intensity_at((3, 4)) == 0.6
    assert field.intensity_at((3, 5)) == 0.3
    assert field.intensity_at((3, 6)) == 0.0  # outside the 5x5 window


def test_deposit_below_min_center_gate_is_a_hard_error() -> None:
    field = make_field()
    with pytest.raises(ScentEmissionError):
        field.deposit((3, 3), MIN_CENTER - 0.1)
    assert field.cells() == {}  # the refused deposit left no trace


def test_deposit_at_gate_threshold_is_allowed() -> None:
    field = make_field()
    field.deposit((3, 3), MIN_CENTER)
    assert field.intensity_at((3, 3)) == MIN_CENTER


def test_max_merge_a_weaker_overlapping_deposit_never_lowers_cells() -> None:
    field = make_field()
    field.deposit((3, 3), CENTER)
    field.deposit((3, 4), MIN_CENTER)  # its center 0.5 < existing ring-1 value 0.6
    assert field.intensity_at((3, 4)) == 0.6
    assert field.intensity_at((3, 3)) == 0.9


def test_decay_clamps_at_zero_and_keeps_the_cell_known() -> None:
    field = make_field()
    field.absorb({"1,1": 0.05})
    field.decay()
    assert field.cells() == {(1, 1): 0.0}
    assert field.intensity_at((1, 1)) == 0.0


def test_decay_rounds_to_three_decimals() -> None:
    field = make_field()
    field.absorb({"2,2": 0.9005})
    field.decay()
    assert field.intensity_at((2, 2)) == 0.8


def test_snapshot_is_sparse_positive_only_with_wire_keys() -> None:
    field = make_field()
    field.absorb({"1,1": 0.1, "2,2": 0.4})
    field.decay()  # (1,1) hits the floor and must drop out of the wire form
    assert field.snapshot() == {"2,2": 0.3}


def test_absorb_max_merges_and_ignores_off_board_keys() -> None:
    field = make_field()
    field.deposit((3, 3), CENTER)
    field.absorb({"3,3": 0.2, "0,0": 0.7, "9,9": 0.5, "-1,3": 0.5})
    assert field.intensity_at((3, 3)) == 0.9  # weaker inbound never lowers
    assert field.intensity_at((0, 0)) == 0.7
    assert (9, 9) not in field.cells()
    assert (-1, 3) not in field.cells()


def test_origin_one_board_clips_below_the_start_index() -> None:
    field = make_field(origin=1)
    field.deposit((1, 1), CENTER)
    cells = field.cells()
    assert (0, 0) not in cells
    assert (0, 1) not in cells
    assert field.intensity_at((1, 1)) == 0.9
    assert field.intensity_at((3, 3)) == 0.3  # ring-2 still inside a 7-wide board at origin 1


def test_sq1_order_deposit_then_decay_yields_the_locked_example() -> None:
    # PRD_scent §2: a just-laid trail transmits 0.8 center / 0.5 ring-1 / 0.2 ring-2.
    field = make_field()
    field.deposit((3, 3), CENTER)
    field.decay()
    snap = field.snapshot()
    assert snap["3,3"] == 0.8
    assert snap["3,4"] == 0.5
    assert snap["3,5"] == 0.2


def test_two_fields_replaying_the_same_ops_are_identical() -> None:
    ops_a, ops_b = make_field(), make_field()
    for field in (ops_a, ops_b):
        field.deposit((3, 3), CENTER)
        field.decay()
        field.deposit((3, 4), CENTER)
        field.absorb({"5,5": 0.4})
    assert ops_a.cells() == ops_b.cells()
    assert ops_a.snapshot() == ops_b.snapshot()

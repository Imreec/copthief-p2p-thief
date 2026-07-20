"""Kit conformance for `multiplicative_book_v1` (SPEC §5.1, PROMOTED; CLAUDE.md §1 #13).

The vectors drive OUR model — never a vendored checker. Passing means the book-model
physics we would play under a pair-lock are the ones anrbj666's independent
implementation reproduced byte-exact, so a scent dispute reduces to a hash.

Evaluation order is load-bearing here: the book model rounds nothing, so
`(1-rho)*tau + delta` and `tau - rho*tau + delta` differ in the last IEEE-754 bit on a
known 75/534 of inputs (ADR-0004 v2). The `ordering_probe` vectors pin the form.
"""

import json
from pathlib import Path
from typing import Any

from copthief_core.domain.scent import ScentField
from copthief_core.domain.scent_book import MultiplicativeBookV1
from copthief_core.domain.scent_models import make_scent_model

VECTORS = Path(__file__).parent / "vectors"


def _load(name: str) -> dict[str, Any]:
    return json.loads((VECTORS / name).read_text(encoding="utf-8"))


BOOK = _load("scent_book_v3.json")


def _model() -> MultiplicativeBookV1:
    model = make_scent_model("multiplicative_book_v1", params=BOOK["model"]["params"])
    assert isinstance(model, MultiplicativeBookV1)
    return model


def _field(board_size: int) -> ScentField:
    return ScentField(board_size=board_size, model=_model())


def test_kernel_matches_the_printed_figure_4_table_verbatim() -> None:
    assert _model().kernel == [tuple(row) for row in BOOK["kernel"]]


def test_emit_vectors_reproduce_the_deposited_field() -> None:
    for vector in BOOK["emit"]:
        field = _field(7)
        field.advance(tuple(vector["center"]))
        assert field.snapshot() == vector["field"], vector.get("note")


def test_scalar_traces_reproduce_including_pure_decay_and_the_upper_clamp() -> None:
    model = _model()
    for key in ("pure_decay", "clamp"):
        trace = BOOK["scalar_traces"][key]
        assert model.step_cell(trace["tau"], trace["delta"]) == trace["after"], trace["note"]


def test_the_three_turn_scalar_chain_reproduces_from_an_empty_start() -> None:
    chain = BOOK["scalar_traces"]["chain"]
    model, tau = _model(), 0.0
    for entry in chain["steps"]:
        tau = model.step_cell(tau, entry["delta"])
        assert tau == entry["tau"], chain["note"]


def test_the_chain_forks_on_the_shared_predecessor() -> None:
    """The turn-3 fork: the pair shares predecessor 0.758 under deltas 0.20 / 0.14."""
    chain = BOOK["scalar_traces"]["chain"]
    model, tau = _model(), 0.0
    for entry in chain["steps"][:-1]:
        tau = model.step_cell(tau, entry["delta"])
    assert model.step_cell(tau, 0.14) == chain["fork_at_turn_3_with_delta_0_14"]


def test_pinned_evaluation_order_is_the_one_the_kit_probed() -> None:
    """Not algebra — IEEE-754. The alternative order is wrong in the last bit."""
    model = _model()
    for case in BOOK["ordering_probe"]["cases"]:
        assert model.step_cell(case["tau"], case["delta"]) == case["pinned_order"]
        if not case["equal"]:
            assert model.step_cell(case["tau"], case["delta"]) != case["alternative_order"]


def test_field_walk_reproduces_three_full_turns_of_a_moving_trail() -> None:
    walk = BOOK["field_walk"]
    field = _field(walk["board_size"])
    for turn in walk["turns"]:
        field.advance(tuple(turn["center"]))
        assert field.snapshot() == turn["field"], f"turn {turn['turn']}: {walk['note']}"


def test_the_two_models_diverge_after_one_turn_on_an_empty_board() -> None:
    """The whole reason the lock exists: same board, same move, different bytes."""
    divergence = BOOK["divergence_vs_reference"]
    center = tuple(divergence["center"])
    book = _field(7)
    book.advance(center)
    assert book.snapshot() == divergence["multiplicative_book_v1"]

    reference = ScentField(board_size=7, window=5, decay=0.1, min_center_intensity=0.5)
    reference.deposit(center, 0.9)
    assert reference.snapshot() == divergence["subtractive_chebyshev_v1"]
    assert (book.snapshot() == reference.snapshot()) is divergence["identical"]

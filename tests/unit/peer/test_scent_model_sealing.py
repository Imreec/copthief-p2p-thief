"""M3-8 step-0 sealing + the M6-7 comparison mode (ADR-0004 v2 decisions 4 and its
consequences section).

v1's known gap was that the locked-model doc was hashed and LOGGED but never
commit-bound — a peer could declare one model and play another with nothing in the
record to contradict it. The hash now enters the step-0 sealed spec record, so the
declaration is tamper-evident under the same commit chain as every turn.
"""

import math
from pathlib import Path

from copthief_core.domain.crypto import commit as crypto_commit
from copthief_core.peer.scent_check import scent_physics_mismatches
from copthief_core.peer.sealing import live_spec_record
from copthief_core.shared.config import load_all
from copthief_core.shared.locked_models import SCENT_MODEL

CONSTITUTION, PRIVATE, _LIMITS = load_all(Path("config"), counted=False)


def test_the_step_0_record_seals_the_declared_model_hash() -> None:
    record = live_spec_record(PRIVATE, CONSTITUTION)
    expected = PRIVATE.locked_models.hash(SCENT_MODEL, PRIVATE.scent_model)
    assert record.payload["scent_model_sha256"] == expected


def test_the_sealed_hash_is_the_one_the_handshake_declares() -> None:
    """Declaration and seal must be the same value or the lock proves nothing."""
    from copthief_core.peer.session import PeerSession

    session = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=1)
    declared = session.negotiate_payload()["scent_model_sha256"]
    assert live_spec_record(PRIVATE, CONSTITUTION).payload["scent_model_sha256"] == declared


def test_tampering_with_the_sealed_model_hash_breaks_the_commit() -> None:
    """The point of decision 4: swapping the declared model invalidates the record."""
    record = live_spec_record(PRIVATE, CONSTITUTION)
    assert crypto_commit(record.payload, record.nonce) == record.commit
    forged = dict(record.payload)
    forged["scent_model_sha256"] = PRIVATE.locked_models.hash(SCENT_MODEL, "multiplicative_book_v1")
    assert crypto_commit(forged, record.nonce) != record.commit


def _walk(steps: int) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """A short honest walk: revealed records plus the grids they imply."""
    from copthief_core.domain.scent import ScentField

    field = ScentField(
        board_size=CONSTITUTION.board.grid_size,
        window=CONSTITUTION.pheromones.grid_size,
        decay=CONSTITUTION.pheromones.decay,
        min_center_intensity=CONSTITUTION.pheromones.min_center_intensity,
        origin=CONSTITUTION.board.axis_start_index,
    )
    records: list[dict[str, object]] = []
    inbound: list[dict[str, object]] = []
    for step in range(1, steps + 1):
        position = (step % CONSTITUTION.board.grid_size, 1)
        field.advance(position, CONSTITUTION.pheromones.center_intensity)
        records.append({"payload": {"step": step, "position": list(position)}})
        inbound.append({"step": step, "smell_grid": field.snapshot()})
    return records, inbound


def test_the_rounding_model_is_compared_byte_wise_tolerance_ignored() -> None:
    """The reference form is round-3 exact, so a difference of ANY size is a difference
    — a generous tolerance must not soften it."""
    records, inbound = _walk(3)
    fudged = dict(inbound[-1]["smell_grid"])  # type: ignore[arg-type]
    cell = next(iter(fudged))
    fudged[cell] = fudged[cell] + 1e-12
    inbound[-1]["smell_grid"] = fudged
    mismatches = scent_physics_mismatches(
        records=records,
        inbound=inbound,
        constitution=CONSTITUTION,
        private=PRIVATE,
        tolerance=1.0,
    )
    assert [m["step"] for m in mismatches] == [3]


def test_an_honest_walk_is_clean_under_the_shipped_model() -> None:
    records, inbound = _walk(4)
    assert (
        scent_physics_mismatches(
            records=records, inbound=inbound, constitution=CONSTITUTION, private=PRIVATE
        )
        == []
    )


def _book_private() -> object:
    from dataclasses import replace

    return replace(PRIVATE, scent_model="multiplicative_book_v1")


def test_a_last_bit_difference_is_forgiven_under_the_no_rounding_model() -> None:
    """The 75/534 case: two HONEST peers differ in the last IEEE-754 bit because each
    side recomputes rather than receives. Byte-wise there would manufacture evidence."""
    from copthief_core.domain.scent import ScentField
    from copthief_core.domain.scent_models import make_scent_model

    private = _book_private()
    doc = PRIVATE.locked_models.doc(SCENT_MODEL, "multiplicative_book_v1")
    field = ScentField(
        board_size=CONSTITUTION.board.grid_size,
        origin=CONSTITUTION.board.axis_start_index,
        model=make_scent_model("multiplicative_book_v1", params=doc["params"]),
    )
    records: list[dict[str, object]] = []
    inbound: list[dict[str, object]] = []
    for step in range(1, 4):
        position = (step % CONSTITUTION.board.grid_size, 1)
        field.advance(position)
        records.append({"payload": {"step": step, "position": list(position)}})
        grid = dict(field.snapshot())
        cell = next(iter(grid))
        # One ULP away — what the alternative evaluation order actually produces.
        grid[cell] = math.nextafter(grid[cell], math.inf)
        inbound.append({"step": step, "smell_grid": grid})

    common = {"records": records, "inbound": inbound, "constitution": CONSTITUTION}
    assert scent_physics_mismatches(**common, private=private, tolerance=1e-9) == []
    # ...and byte-wise the same honest data would have been flagged at every step.
    assert len(scent_physics_mismatches(**common, private=private, tolerance=0.0)) == 3

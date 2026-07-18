"""Kit CORE conformance (CLAUDE.md §1 #13): domain/scent reproduces every pheromone vector.

The vectors drive OUR ScentField (never a vendored checker) — `emit` vectors through a
fresh field's deposit+snapshot, `decay` vectors through absorb+decay. Passing means the
grids we transmit are the byte-level construction every conformant team expects
(kit SPEC §5), so their belief maps read our trail as the book describes.
"""

import json
from pathlib import Path
from typing import Any

from copthief_core.domain.scent import ScentField

VECTORS = Path(__file__).parent / "vectors"


def _load(name: str) -> dict[str, Any]:
    return json.loads((VECTORS / name).read_text(encoding="utf-8"))


def _field(vector: dict[str, Any]) -> ScentField:
    """A fresh field sized per the vector; gate/decay params never bind emit math."""
    return ScentField(
        board_size=vector["board_size"],
        window=vector["grid_size"],
        decay=0.0,
        min_center_intensity=0.0,
    )


def test_emit_vectors_reproduce_snapshot_fields() -> None:
    for vector in _load("pheromone.json")["emit"]:
        field = _field(vector)
        field.deposit(tuple(vector["center"]), vector["intensity"])
        assert field.snapshot() == vector["field"], vector.get("note")


def test_decay_vectors_reproduce_including_zero_clamp() -> None:
    for vector in _load("pheromone.json")["decay"]:
        field = ScentField(
            # Bound above every key in the vectors; decay math never reads the bound.
            board_size=64,
            window=5,
            decay=vector["decay"],
            min_center_intensity=0.0,
        )
        field.absorb(vector["before"])
        field.decay()
        assert field.cells() == {
            tuple(int(part) for part in key.split(",")): value
            for key, value in vector["after"].items()
        }, vector.get("note")

"""Locked scent-model document (PRD_scent §4): the handshake artifact, byte-pinned.

A scent-model dispute must be diagnosable to a hash, not to prose — so the document's
canonical bytes are pinned literally here (shipped-config values), and two independent
builds must hash identically (the §8 acceptance criterion for our two peers).
"""

from copthief_core.domain.crypto import canonical_hash, canonical_str
from copthief_core.domain.scent import locked_model_document

# Shipped-config `pheromones` values, restated as test inputs only.
SHIPPED = {
    "center_intensity": 0.9,
    "decay": 0.1,
    "grid_size": 5,
    "min_center_intensity": 0.5,
}

# The exact canonical bytes both peers must derive for the shipped config — any drift
# (a key rename, float repr, ring-count change) breaks this pin before it breaks a game.
PINNED_CANONICAL = (
    '{"example":{"deposited_by_ring":[0.9,0.6,0.3],'
    '"transmitted_by_ring":[0.8,0.5,0.2]},'
    '"formula":"subtractive_chebyshev_v1",'
    '"params":{"pheromone_center_intensity":0.9,"pheromone_decay":0.1,'
    '"pheromone_grid_size":5,"pheromone_min_center_intensity":0.5}}'
)


def test_locked_model_document_canonical_bytes_are_pinned() -> None:
    document = locked_model_document(**SHIPPED)
    assert canonical_str(document) == PINNED_CANONICAL


def test_two_independent_builds_hash_identically() -> None:
    ours = locked_model_document(**SHIPPED)
    theirs = locked_model_document(**SHIPPED)
    assert canonical_hash(ours) == canonical_hash(theirs)


def test_example_rings_follow_deposit_then_decay_order() -> None:
    # SQ1: the transmitted example is the deposited example after ONE decay, clamped.
    document = locked_model_document(**SHIPPED)
    deposited = document["example"]["deposited_by_ring"]
    transmitted = document["example"]["transmitted_by_ring"]
    assert len(deposited) == SHIPPED["grid_size"] // 2 + 1
    assert transmitted == [round(value - SHIPPED["decay"], 3) for value in deposited]


def test_document_tracks_its_input_values_not_constants() -> None:
    document = locked_model_document(
        center_intensity=0.6, decay=0.2, grid_size=3, min_center_intensity=0.1
    )
    assert document["params"]["pheromone_grid_size"] == 3
    assert document["example"]["deposited_by_ring"] == [0.6, 0.3]
    assert document["example"]["transmitted_by_ring"] == [0.4, 0.1]

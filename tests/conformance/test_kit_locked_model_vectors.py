"""Kit CORE conformance for locked-model declarations (SPEC §7; CLAUDE.md §1 #13).

Two things must hold for a lock to be an interop artifact rather than a private ritual:
our committed registrations must hash to the KIT's pins byte-for-byte, and the refusal
rule must behave exactly as the five-row truth table says. The table is a fixture
because it is BEHAVIOUR, not bytes — and it is the part implementations get wrong.
"""

import json
from pathlib import Path
from typing import Any

from copthief_core.shared.locked_models import (
    LockedModelRegistry,
    load_locked_models,
    lock_decision,
)

VECTORS = Path(__file__).parent / "vectors"
KIT: dict[str, Any] = json.loads((VECTORS / "locked_model.json").read_text(encoding="utf-8"))
REGISTRY = load_locked_models(Path("config/locked_models.json"))


def test_the_doc_schema_is_the_four_key_envelope() -> None:
    assert KIT["doc_schema"]["keys"] == ["family", "name", "params", "example"]
    assert KIT["doc_schema"]["declared_key"] == "<family>_sha256"


def test_every_registered_doc_hashes_to_the_kit_pin() -> None:
    """All six, across all three families — scent models, wire shapes, info modes."""
    for entry in KIT["registered"]:
        doc = entry["doc"]
        assert REGISTRY.doc(doc["family"], doc["name"]) == doc, doc["name"]
        assert REGISTRY.hash(doc["family"], doc["name"]) == entry["sha256"], doc["name"]


def test_our_registry_carries_every_kit_registration() -> None:
    """A missing registration is a lock we could not name if a partner declared it."""
    expected = {f"{e['doc']['family']}:{e['doc']['name']}" for e in KIT["registered"]}
    assert expected <= set(REGISTRY.docs)


def test_the_declaration_example_reproduces_from_our_registry() -> None:
    """What actually crosses the wire: hashes only, one per family."""
    for family, declared in KIT["declaration_example"].items():
        if not family.endswith("_sha256"):
            continue  # the fixture's prose `note`
        assert LockedModelRegistry.declared_key(family[: -len("_sha256")]) == family
        assert any(REGISTRY.hash(*key.split(":")) == declared for key in REGISTRY.docs)


def test_the_refusal_truth_table_reproduces_row_for_row() -> None:
    """Five rows; exactly ONE refuses. Omission is never refusal, in either direction."""
    for row in KIT["refusal_rule"]:
        assert lock_decision(row["ours"], row["theirs"]) == row["decision"], row["note"]
    assert sum(r["decision"] == "refuse" for r in KIT["refusal_rule"]) == 1

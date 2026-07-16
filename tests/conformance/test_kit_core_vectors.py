"""Kit CORE conformance (CLAUDE.md §1 #13): our domain/crypto reproduces every fixture.

These tests drive OUR implementation (never a vendored checker) over the kit's vectors —
passing means our bytes are compatible with every other conformant team: signatures verify,
both peers derive the same game_uid, and the opponent's audit re-hash of our revealed log
matches instead of raising a false tamper_forfeit (kit SPEC §7).
"""

import hashlib
import json
from pathlib import Path
from typing import Any

from copthief_core.domain.crypto import (
    canonical_hash,
    canonical_str,
    commit,
    game_uid,
    terms_signature,
    verify,
)

VECTORS = Path(__file__).parent / "vectors"


def _load(name: str) -> dict[str, Any]:
    return json.loads((VECTORS / name).read_text(encoding="utf-8"))


def test_canonical_json_vectors_reproduce_strings_and_hashes() -> None:
    for vector in _load("canonical_json.json")["vectors"]:
        assert canonical_str(vector["object"]) == vector["canonical"], vector.get("note")
        assert canonical_hash(vector["object"]) == vector["sha256"], vector.get("note")


def test_commit_vectors_reproduce_and_verify() -> None:
    for vector in _load("commit_reveal.json")["vectors"]:
        got = commit(vector["payload"], vector["nonce"])
        assert got == vector["commit"], vector.get("note")
        assert verify(vector["payload"], vector["nonce"], vector["commit"])


def test_divergent_commit_forms_are_pinned_and_mutually_distinct() -> None:
    # The release's three published constructions over one sealed record (kit SPEC §3):
    # ours must equal the reference form and differ from both illustrative book forms.
    dv = _load("commit_reveal.json")["divergent_forms"]
    got_reference = commit(dv["payload"], dv["nonce"])
    got_ch5_listing = canonical_hash({**dv["payload"], "nonce": dv["nonce"]})
    got_audit_snippet = hashlib.sha256(
        f"{dv['nonce']}|{dv['payload']['move']}".encode()
    ).hexdigest()
    assert got_reference == dv["reference_form"]
    assert got_ch5_listing == dv["book_ch5_listing_form"]
    assert got_audit_snippet == dv["book_audit_snippet_form"]
    assert len({got_reference, got_ch5_listing, got_audit_snippet}) == 3


def test_terms_signature_vectors_reproduce() -> None:
    for vector in _load("terms_signature.json")["vectors"]:
        assert terms_signature(vector["terms"], vector["nonce"]) == vector["signature"]


def test_game_uid_vectors_reproduce_and_ignore_group_order() -> None:
    for vector in _load("game_uid.json")["vectors"]:
        got = game_uid(vector["terms"], vector["group_a"], vector["group_b"])
        assert got == vector["game_uid"], vector.get("note")

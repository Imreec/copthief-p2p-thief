"""The consensus signature (PRD_reporting §2): the THIRD canonical variant.

Settlement-critical and credited to Alon: SHA-256 over ``json.dumps(sort_keys=True,
ensure_ascii=False)`` with DEFAULT (spaced) separators — deliberately distinct from the
kit-CORE compact canonical, and the cross-guard here keeps one from ever substituting
for the other. Reference-derived byte vectors live in tests/conformance.
"""

from __future__ import annotations

import hashlib
import json

from copthief_core.domain.crypto import canonical_hash
from copthief_core.report.consensus import consensus_signature

NESTED = {"b": [1, 2], "a": {"y": 0.5, "x": "טקסט"}, "c": None}


def test_consensus_signature_is_key_order_invariant() -> None:
    reordered = {"c": None, "a": {"x": "טקסט", "y": 0.5}, "b": [1, 2]}
    assert consensus_signature(NESTED) == consensus_signature(reordered)


def test_consensus_signature_matches_default_separator_dumps() -> None:
    """Independent spelling of the construction (guards the separators argument)."""
    blob = json.dumps(NESTED, sort_keys=True, ensure_ascii=False)
    assert consensus_signature(NESTED) == hashlib.sha256(blob.encode()).hexdigest()


def test_consensus_signature_differs_from_compact_canonical() -> None:
    """The cross-guard: spaced (consensus) and compact (kit CORE) must never coincide
    on any container payload — a silent swap would break settlement byte-agreement."""
    assert consensus_signature(NESTED) != canonical_hash(NESTED)


def test_consensus_signature_keeps_hebrew_unescaped() -> None:
    """ensure_ascii=False is load-bearing: the Hebrew-keyed report hashes its real
    UTF-8 bytes, not \\uXXXX escapes."""
    data = {"תוצאה": "לכידה"}
    escaped = json.dumps(data, sort_keys=True)  # ensure_ascii default True
    assert consensus_signature(data) != hashlib.sha256(escaped.encode()).hexdigest()

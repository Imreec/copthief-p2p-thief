"""Crypto layer (book ch.5; kit SPEC §2–§4): the byte-level constructions of the protocol.

Re-derived from the conformance kit's CORE definitions (kit commit pinned in
tests/conformance/SOURCE.md) and verified against its vectors in CI — never ported from
the reference implementation (ADR-0002). This module is the repo's ONLY serialization
call site with hashing intent (PRD_crypto §2): terms, sealing, audit, and the M6 report
emitter all consume these functions.

The commit construction is the reference form — one of three the book v3.0.0 publishes;
the kit pins it as the only cryptographically sufficient one (it binds `state` and
`intent`; the audit-snippet form does not). Kit SPEC §3 carries the full analysis.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid

# 16 random bytes -> 32 hex chars, matching every kit vector's nonce length.
_NONCE_BYTES = 16


def canonical_str(obj: object) -> str:
    """The one canonical form (kit §2): sorted keys, compact separators, native UTF-8.

    `ensure_ascii=False` is load-bearing: the opponent re-hashes our revealed hints at
    audit, and an escaped `א` produces a different hash — a false tamper for both sides.
    """
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def canonical_bytes(obj: object) -> bytes:
    """UTF-8 bytes of the canonical string — the exact preimage of every protocol hash."""
    return canonical_str(obj).encode("utf-8")


def canonical_hash(obj: object) -> str:
    """SHA-256 hex digest over the canonical bytes."""
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def make_nonce() -> str:
    """A fresh cryptographic nonce (`secrets`, never `random` — book ch.5; App E).

    One nonce per sealed record; withheld until the end-of-game audit (PRD_crypto §4).
    """
    return secrets.token_hex(_NONCE_BYTES)


def commit(payload: object, nonce: str) -> str:
    """Seal a record: SHA256(canonical_json(payload) + "|" + nonce) — kit §3.

    The nonce is pipe-appended to the canonical string, NOT placed inside the hashed
    object (that is the book's ch.5 listing form, which hashes differently).
    """
    return hashlib.sha256(f"{canonical_str(payload)}|{nonce}".encode()).hexdigest()


def verify(payload: object, nonce: str, sealed_commit: str) -> bool:
    """Re-derive a revealed record's commit with OUR serializer; constant-time compare.

    Run at audit over every opponent record — any mismatch is proof of tampering and
    voids the mini-game (0/0). Also self-run over our own log before sending it.
    """
    return secrets.compare_digest(commit(payload, nonce), sealed_commit)


def terms_signature(terms: object, nonce: str) -> str:
    """Pre-game agreement gate (kit §4): the commit construction over the agreed terms.

    Each peer signs with its own nonce; we re-verify the opponent's signature over the
    terms WE hold (which must value-equal theirs) using their nonce — any byte drift
    (a value, a key name, float repr, escaping) refuses the game before it starts.
    """
    return commit(terms, nonce)


def game_uid(terms: object, group_a: str, group_b: str) -> str:
    """The shared deterministic game id (kit §4) — no round-trip needed.

    UUID over the first 16 digest bytes of SHA256(canonical(terms)|sorted group ids);
    sorting makes it order-independent. Names all four submission artifacts
    (declaration/config/log/result — App F table 20) so match files never mix.
    """
    pair = sorted([group_a, group_b])
    seed = f"{canonical_str(terms)}|{'|'.join(pair)}"
    return str(uuid.UUID(bytes=hashlib.sha256(seed.encode()).digest()[:_NONCE_BYTES]))

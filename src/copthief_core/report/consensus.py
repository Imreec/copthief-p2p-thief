"""The consensus signature — the settlement canonical (book §8; PRD_reporting §2).

A THIRD canonical variant beside the kit-CORE compact form (`domain/crypto`):
SHA-256 over ``json.dumps(data, sort_keys=True, ensure_ascii=False)`` with the
DEFAULT (spaced) separators. Find credited to Alon (league coordination), verified
against the reference `report_writer.py` @960499fd. The distinct module + name exist
so this form can never silently substitute for the compact wire canonical — the two
disagree on every container payload, and settlement byte-agreement with other teams
depends on using exactly this one for report signatures.

Usage sites (all sign-then-insert where a key is embedded): the Hebrew report's
``חתימת_קונסנזוס_משותפת`` · the log artifact's records hash · the result artifact's
symmetric-outcome hash · each declaration group block's ``signature``.
"""

from __future__ import annotations

import hashlib
import json


def consensus_signature(data: object) -> str:
    """SHA-256 hex over the spaced-separator sorted-keys JSON of `data`.

    Input: any JSON-serializable object. Output: 64-char lowercase hex digest.
    Key order never matters; Hebrew (any non-ASCII) hashes as real UTF-8 bytes.
    """
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()

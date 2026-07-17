"""Primitive wire-field checkers: each returns a problem string or None.

Collected (never short-circuited) so one rejection names every problem at once — an
interop failure with another team should be diagnosable from a single log line.
"""

from __future__ import annotations

import re
from typing import Any

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_GRID_KEY = re.compile(r"^-?\d+,-?\d+$")


class WireValidationError(ValueError):
    """An inbound message failed validation; `problems` lists every offending field."""

    def __init__(self, message_type: str, problems: list[str]) -> None:
        self.problems = problems
        super().__init__(f"{message_type} rejected: " + "; ".join(problems))


def check_int(raw: dict[str, Any], key: str, *, minimum: int | None = None) -> str | None:
    """Required integer (bool excluded), optionally bounded below."""
    value = raw.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        return f"{key}: required int, got {value!r}"
    if minimum is not None and value < minimum:
        return f"{key}: must be >= {minimum}, got {value!r}"
    return None


def check_str(raw: dict[str, Any], key: str, *, non_empty: bool = False) -> str | None:
    """Required string, optionally non-empty."""
    value = raw.get(key)
    if not isinstance(value, str) or (non_empty and not value):
        return f"{key}: required {'non-empty ' if non_empty else ''}str, got {value!r}"
    return None


def _is_cell(value: object) -> bool:
    """A `[row, col]` int pair (bools excluded) — the wire's cell shape."""
    return (
        isinstance(value, list | tuple)
        and len(value) == 2
        and all(isinstance(v, int) and not isinstance(v, bool) for v in value)
    )


def check_optional_claim_response(raw: dict[str, Any], key: str) -> str | None:
    """Optional reference-shaped `{"claim": [r, c], "caught": bool}` (null/absent fine)."""
    value = raw.get(key)
    if value is None:
        return None
    if (
        isinstance(value, dict)
        and _is_cell(value.get("claim"))
        and isinstance(value.get("caught"), bool)
    ):
        return None
    return f'{key}: must be {{"claim": [r, c], "caught": bool}} when present, got {value!r}'


def check_optional_win_claim(raw: dict[str, Any], key: str) -> str | None:
    """Optional reference-shaped `{"type": <non-empty str>}` (null/absent fine)."""
    value = raw.get(key)
    if value is None:
        return None
    if isinstance(value, dict) and isinstance(value.get("type"), str) and value["type"]:
        return None
    return f'{key}: must be {{"type": str}} when present, got {value!r}'


def check_hex64(raw: dict[str, Any], key: str) -> str | None:
    """Required 64-char lowercase hex digest (a SHA-256 commit)."""
    value = raw.get(key)
    if not isinstance(value, str) or not _HEX64.match(value):
        return f"{key}: required 64-char lowercase hex, got {value!r}"
    return None


def check_smell_grid(raw: dict[str, Any], key: str) -> str | None:
    """Required `{"r,c": intensity}` mapping (the reference's wire form, kit §5)."""
    value = raw.get(key)
    if not isinstance(value, dict):
        return f"{key}: required dict of 'r,c' -> intensity, got {type(value).__name__}"
    for cell, intensity in value.items():
        if not isinstance(cell, str) or not _GRID_KEY.match(cell):
            return f"{key}: bad cell key {cell!r} (expected 'r,c')"
        if not isinstance(intensity, int | float) or isinstance(intensity, bool):
            return f"{key}: bad intensity {intensity!r} for cell {cell!r}"
    return None


def check_optional_cell(raw: dict[str, Any], key: str) -> str | None:
    """Optional `[row, col]` int pair (explicit null fine — the reference emits nulls)."""
    value = raw.get(key)
    if value is None or _is_cell(value):
        return None
    return f"{key}: must be [row, col] ints when present, got {value!r}"

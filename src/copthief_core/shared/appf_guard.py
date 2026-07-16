"""App F validation guard (book App F §1–§2; PRD_engine §4–§5; CLAUDE.md §1 #15).

Input: a raw `game.json` mapping + the App F transcription (`config/app_f_table.json`).
Output: the list of violations — empty means the constitution is signable/loadable.

The statuses' binding semantics: **fixed** — any deviation from the default disqualifies;
**minimum** — negotiation may only go at-or-above the default (the example value is the
floor AND the default absent agreement); **negotiable** — any agreed value. A parameter
missing from the config is itself a violation (App F §2: ALL values must be defined and
locked). The defaults live in the data file, never in this code (CLAUDE.md §1 #5).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCOPE_ALWAYS = "always"
SCOPE_COUNTED = "counted_series"


@dataclass(frozen=True)
class AppFEntry:
    """One row of the binding table: status, book default, scope, optionality.

    `optional` marks reference-only parameters absent from the App B schema (e.g. the
    pheromone emission gate) — validated when present, but never required to exist.
    """

    status: str
    default: Any
    scope: str = SCOPE_ALWAYS
    optional: bool = False


@dataclass(frozen=True)
class AppFTable:
    """The App F transcription, keyed by dotted `section.parameter` names."""

    version: str
    entries: dict[str, AppFEntry]

    @classmethod
    def load(cls, path: Path) -> AppFTable:
        """Read the transcription data file (Input: path; Output: table; Raises: OSError/KeyError on a malformed file)."""
        raw = json.loads(path.read_text(encoding="utf-8"))
        entries = {
            key: AppFEntry(
                status=spec["status"],
                default=spec["default"],
                scope=spec.get("scope", SCOPE_ALWAYS),
                optional=spec.get("optional", False),
            )
            for key, spec in raw["parameters"].items()
        }
        return cls(version=raw["version"], entries=entries)


def _lookup(config: dict[str, Any], dotted_key: str) -> tuple[bool, object]:
    """(present, value) for a dotted `section.parameter` key in the raw config mapping."""
    section_name, _, param = dotted_key.partition(".")
    section = config.get(section_name)
    if not isinstance(section, dict) or param not in section:
        return False, None
    return True, section[param]


def _check(key: str, entry: AppFEntry, value: object) -> str | None:
    """One parameter against its App F row; None when compliant."""
    if entry.status == "fixed" and value != entry.default:
        return f"{key}: fixed at {entry.default!r} by App F, got {value!r} (deviation disqualifies)"
    if entry.status == "minimum":
        floor = entry.default
        if not isinstance(value, int | float) or not isinstance(floor, int | float):
            return f"{key}: App F minimum parameters are numeric, got {value!r}"
        if value < floor:
            return f"{key}: App F minimum is {floor!r}, got {value!r} (may only be raised)"
    return None


def validate_constitution(config: dict[str, Any], table: AppFTable, *, counted: bool) -> list[str]:
    """Every App F parameter checked; `counted` arms the counted-series-scoped rows.

    PRD_engine §6.1: `num_games` is fixed at six for a counted match; the App B
    single-sample default (1) is legal only outside counted series.
    """
    violations: list[str] = []
    for key, entry in table.entries.items():
        if entry.scope == SCOPE_COUNTED and not counted:
            continue
        present, value = _lookup(config, key)
        if not present:
            if not entry.optional:
                violations.append(
                    f"{key}: missing — App F requires every parameter defined and locked"
                )
            continue
        problem = _check(key, entry, value)
        if problem is not None:
            violations.append(problem)
    return violations

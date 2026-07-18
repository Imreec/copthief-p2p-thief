"""Arena config loader (M5-2; PRD_police_brain §4): `config/arena.json`, typed.

Per-repo by design: rosters name this repo's own role package (book §6.2 dotted
`package.module:Class` specs with a display alias), so the file is never mirrored —
the mirrored scripts/tests read whatever the local copy lists. Referee-mode
instrument only; nothing here is negotiated or crosses the wire.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from copthief_core.shared.private_config import ConfigError, validated_version


@dataclass(frozen=True)
class RosterEntry:
    """One arena brain: display alias + factory spec (core name or dotted path)."""

    name: str
    spec: str


@dataclass(frozen=True)
class DodSeries:
    """One configured win-rate floor: a head-to-head scenario series, CI-blocking."""

    label: str
    police: str
    thief: str
    wins_role: str
    min_win_rate: float
    seeds: tuple[int, ...]


@dataclass(frozen=True)
class ArenaConfig:
    """The typed `config/arena.json` (Input: parsed file; Output: roster queries)."""

    version: str
    police_roster: tuple[RosterEntry, ...]
    thief_roster: tuple[RosterEntry, ...]
    seeds: tuple[int, ...]
    scenario_min_separation: int
    brain_options: dict[str, dict[str, float]]
    dod_series: tuple[DodSeries, ...]
    evidence_out: str

    def options_for(self, name: str) -> dict[str, float]:
        """The per-brain options block for `name` (empty when none is configured)."""
        return dict(self.brain_options.get(name, {}))

    def spec_for(self, name: str) -> str:
        """The factory spec behind a roster alias (KeyError-loud on unknown names)."""
        for entry in (*self.police_roster, *self.thief_roster):
            if entry.name == name:
                return entry.spec
        raise KeyError(f"no roster entry named {name!r}")


def _entry(raw: str | dict[str, Any]) -> RosterEntry:
    if isinstance(raw, str):
        return RosterEntry(name=raw, spec=raw)
    return RosterEntry(name=str(raw["name"]), spec=str(raw["spec"]))


def _dod(raw: dict[str, Any]) -> DodSeries:
    return DodSeries(
        label=str(raw["label"]),
        police=str(raw["police"]),
        thief=str(raw["thief"]),
        wins_role=str(raw["wins_role"]),
        min_win_rate=float(raw["min_win_rate"]),
        seeds=tuple(int(s) for s in raw["seeds"]),
    )


def load_arena_config(path: Path) -> ArenaConfig:
    """Load + validate the arena instrument config (Raises: ConfigError on bad shape)."""
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    try:
        return ArenaConfig(
            version=validated_version(raw, path.name),
            police_roster=tuple(_entry(e) for e in raw["police_roster"]),
            thief_roster=tuple(_entry(e) for e in raw["thief_roster"]),
            seeds=tuple(int(s) for s in raw["seeds"]),
            scenario_min_separation=int(raw["scenario_min_separation"]),
            brain_options={
                str(name): {str(k): float(v) for k, v in opts.items()}
                for name, opts in raw.get("brain_options", {}).items()
            },
            dod_series=tuple(_dod(d) for d in raw.get("dod_series", [])),
            evidence_out=str(raw["evidence_out"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ConfigError(f"{path.name}: malformed arena config — {error}") from error

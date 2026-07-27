"""Arena harness (TODO M3-6; PLAN §8): seeded round-robin + champion regression gate.

An sdk CONSUMER: every game runs through SimulationSdk.referee_series (PLAN §3 — no
consumer touches domain/peer directly). The champion pin (`config/arena_champion.json`)
is the CI gate CLAUDE.md §5 mandates: a new brain must not lose to the previous
champion — `champion_regression` lists every dethroning, and the integration suite
runs it blocking on the shipped pin.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from copthief_core.domain.rules import Outcome
from copthief_core.domain.scoring import scores_for
from copthief_core.sdk.arena_config import ArenaConfig
from copthief_core.strategy.info_feed import BeliefFeed
from copthief_core.strategy.referee import RefereeGameResult

if TYPE_CHECKING:
    from copthief_core.sdk.simulation import SimulationSdk

_ROLES = ("police", "thief")


@dataclass(frozen=True)
class PairingSeries:
    """One (police brain, thief brain) pairing's seeded series."""

    police_brain: str
    thief_brain: str
    results: tuple[RefereeGameResult, ...]


@dataclass(frozen=True)
class RoleStanding:
    """One brain's aggregate in one role across the whole round-robin."""

    brain: str
    role: str
    games: int
    wins: int
    points: int


@dataclass(frozen=True)
class ArenaReport:
    """The round-robin's series + per-role standings (best first within each role)."""

    series: tuple[PairingSeries, ...]
    standings: tuple[RoleStanding, ...]

    def standing(self, brain: str, role: str) -> RoleStanding:
        """The (brain, role) row; KeyError-loud if the pairing never played."""
        matches = [s for s in self.standings if s.brain == brain and s.role == role]
        if not matches:
            raise KeyError(f"no standing for {brain!r} as {role!r}")
        return matches[0]


def build_report(
    series: Iterable[PairingSeries], *, scores: Mapping[str, tuple[int, int]]
) -> ArenaReport:
    """Aggregate series into standings (Input: pairing series + outcome→points map
    keyed by Outcome.value; Output: report sorted best-first per role)."""
    tally: dict[tuple[str, str], list[int]] = {}  # (brain, role) -> [games, wins, points]
    for pairing in series:
        for result in pairing.results:
            police_pts, thief_pts = scores.get(result.outcome.value, (0, 0))
            police_row = tally.setdefault((pairing.police_brain, "police"), [0, 0, 0])
            thief_row = tally.setdefault((pairing.thief_brain, "thief"), [0, 0, 0])
            police_row[0] += 1
            thief_row[0] += 1
            police_row[1] += result.outcome is Outcome.COP_CAPTURE
            thief_row[1] += result.outcome is Outcome.THIEF_SURVIVAL
            police_row[2] += police_pts
            thief_row[2] += thief_pts
    standings = tuple(
        sorted(
            (
                RoleStanding(brain=brain, role=role, games=g, wins=w, points=p)
                for (brain, role), (g, w, p) in tally.items()
            ),
            key=lambda s: (s.role, -s.points, -s.wins, s.brain),
        )
    )
    return ArenaReport(series=tuple(series), standings=standings)


def run_round_robin(
    sdk: SimulationSdk, *, config: ArenaConfig, belief_feed: BeliefFeed | None = None
) -> ArenaReport:
    """Every police-roster brain plays every thief-roster brain over the config's
    scenario suite (M5-2 per-role rosters — a role-specific brain only ever enters
    its own side). Standings carry the roster display aliases; `belief_feed` selects
    the wire-shape information structure (default hidden — the shipped arena)."""
    from copthief_core.strategy.scenarios import scenario_suite

    scenarios = scenario_suite(
        sdk.constitution, seeds=config.seeds, min_separation=config.scenario_min_separation
    )
    series = [
        PairingSeries(
            police_brain=police.name,
            thief_brain=thief.name,
            results=tuple(
                sdk.scenario_series(
                    police=police.spec,
                    thief=thief.spec,
                    scenarios=scenarios,
                    police_options=config.options_for(police.name),
                    thief_options=config.options_for(thief.name),
                    belief_feed=belief_feed,
                    thief_feed=thief.feed,
                    scent_model=config.scent_model,
                    claim_threshold=police.claim_threshold,
                    thief_claim_feed=thief.claim_feed,
                )
            ),
        )
        for police in config.police_roster
        for thief in config.thief_roster
    ]
    scores = {
        outcome.value: scores_for(outcome.value, sdk.constitution.scoring) for outcome in Outcome
    }
    return build_report(series, scores=scores)


def load_champions(path: Path) -> dict[str, str]:
    """The pinned champions per role from `config/arena_champion.json`."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {role: str(raw[f"{role}_champion"]) for role in _ROLES}


def champion_regression(report: ArenaReport, champions: Mapping[str, str]) -> list[str]:
    """CLAUDE.md §5 gate: every problem is a dethroning — the pinned champion scored
    below another brain in its role (or never played). Empty list == gate green."""
    problems: list[str] = []
    for role in _ROLES:
        champion = champions.get(role, "")
        rows = [s for s in report.standings if s.role == role]
        try:
            champion_row = next(s for s in rows if s.brain == champion)
        except StopIteration:
            problems.append(f"{role} champion {champion!r} has no arena standing")
            continue
        problems.extend(
            f"{role} champion {champion!r} lost its role table to {row.brain!r} "
            f"({row.points} > {champion_row.points} points)"
            for row in rows
            if row.points > champion_row.points
        )
    return problems

"""GA config loading (M5-4): config-driven, role-blind, referee-mode only.

Fitness = the candidate brain's win-rate for the configured role against the fixed
reference opponent over a fresh scenario-seed suite (never the DoD seeds — the gate
is not a training target). The mirrored copy of this module evolves whatever brain
the LOCAL `config/ga.json` names (PR #29 rule). Fitness itself lives in
`genetic/fitness` since M7-20 (the claim-policy door crossed the file limit).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from copthief_core.shared.private_config import ConfigError, validated_version
from copthief_core.strategy.genetic.genome import GeneSpec


@dataclass(frozen=True)
class GaPhase:
    """One evolution schedule (the committed run, or the CI smoke)."""

    seed: int
    population: int
    generations: int
    elite_count: int
    tournament_size: int
    crossover_blend: float
    mutation_sigma: float
    mutation_rate: float
    fitness_seeds: tuple[int, ...]
    scenario_min_separation: int


@dataclass(frozen=True)
class GaConfig:
    """The typed `config/ga.json`."""

    version: str
    role: str
    brain: str
    opponent: str
    opponent_options: dict[str, float]
    genes: dict[str, tuple[float, float]]
    run: GaPhase
    smoke: GaPhase
    artifact_out: str
    evidence_out: str
    # M7-14 doors, both defaulting to the shipped behavior: the run's named physics
    # and the fixed opponent's information feed (strategy/info_feed.make_feed names).
    scent_model: str | None = None
    opponent_feed: str | None = None
    # M7-15: an OPPONENT POOL — fitness is the plain mean across members (each a
    # {spec, feed?, options?} dict). A GA tuned against one opponent overfits to it
    # (the book-v1 single-opponent retune beat the claim-reader and stalled against
    # a random walker); empty = the single `opponent` above, unchanged.
    opponent_pool: tuple[dict[str, Any], ...] = ()
    # M7-20: evolve UNDER the claim policy we will actually play. `claim_threshold` is
    # run-level because it is a POLICE property and the referee applies it to the police
    # side whichever role is being evolved; `claim_feed` is what an opponent learns on
    # the turns we declared, per member (with this run-level fallback) because the pool's
    # whole point is a mixture where some opponents read our claims and others do not.
    claim_threshold: float | None = None
    claim_feed: str | None = None
    # M11 part 2: the CANDIDATE's own information feed. Every armed brain we field
    # reads a configured feed; None = the historical hidden run (no committed GA
    # artifact is retroactively invalidated by the door landing).
    candidate_feed: str | None = None

    def claim_feed_for(self, member: Mapping[str, Any]) -> str | None:
        """This opponent's claim-reading channel: its own key wins, else the run's."""
        if "claim_feed" in member:
            feed = member["claim_feed"]
            return None if feed is None else str(feed)
        return self.claim_feed

    def spec(self) -> GeneSpec:
        """The search box in fixed (sorted) gene order."""
        names = tuple(sorted(self.genes))
        return GeneSpec(
            names=names,
            low=tuple(self.genes[n][0] for n in names),
            high=tuple(self.genes[n][1] for n in names),
        )


def _phase(raw: dict[str, Any]) -> GaPhase:
    return GaPhase(
        seed=int(raw["seed"]),
        population=int(raw["population"]),
        generations=int(raw["generations"]),
        elite_count=int(raw["elite_count"]),
        tournament_size=int(raw["tournament_size"]),
        crossover_blend=float(raw["crossover_blend"]),
        mutation_sigma=float(raw["mutation_sigma"]),
        mutation_rate=float(raw["mutation_rate"]),
        fitness_seeds=tuple(int(s) for s in raw["fitness_seeds"]),
        scenario_min_separation=int(raw["scenario_min_separation"]),
    )


def load_ga_config(path: Path) -> GaConfig:
    """Load + validate (Raises: ConfigError on bad shape — same posture as arena.json)."""
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    try:
        return GaConfig(
            version=validated_version(raw, path.name),
            role=str(raw["role"]),
            brain=str(raw["brain"]),
            opponent=str(raw["opponent"]),
            opponent_options={str(k): float(v) for k, v in raw.get("opponent_options", {}).items()},
            genes={str(name): (float(box[0]), float(box[1])) for name, box in raw["genes"].items()},
            run=_phase(raw["run"]),
            smoke=_phase(raw["smoke"]),
            artifact_out=str(raw["artifact_out"]),
            evidence_out=str(raw["evidence_out"]),
            scent_model=(None if raw.get("scent_model") is None else str(raw["scent_model"])),
            opponent_feed=(None if raw.get("opponent_feed") is None else str(raw["opponent_feed"])),
            opponent_pool=tuple(dict(member) for member in raw.get("opponent_pool", [])),
            claim_threshold=(
                None if raw.get("claim_threshold") is None else float(raw["claim_threshold"])
            ),
            claim_feed=(None if raw.get("claim_feed") is None else str(raw["claim_feed"])),
            candidate_feed=(
                None if raw.get("candidate_feed") is None else str(raw["candidate_feed"])
            ),
        )
    except (KeyError, TypeError, ValueError, IndexError) as error:
        raise ConfigError(f"{path.name}: malformed GA config — {error}") from error

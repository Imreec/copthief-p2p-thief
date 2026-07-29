"""Locked-model registry (ADR-0004 v2 item 5; kit SPEC §7).

A locked-model doc is DATA, not code: it is copied verbatim from the kit into
`config/locked_models.json`, because `sha256(canonical_json(doc))` is the value we
declare and it must equal the kit's registry pin byte-for-byte. Building the doc in
source would mean two teams implementing the same model from the same spec still
declare different hashes — the failure mode kit SPEC §7 exists to close.

Declaring a model we do not actually run would be worse than declaring nothing, so
`assert_agrees_with` checks the registered params against the signed constitution
wherever the two overlap. A changed pheromone value IS a different model, and must earn
a new registration rather than silently ride the old hash.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from copthief_core.domain.crypto import canonical_hash
from copthief_core.domain.scent_models import ScentModel, make_scent_model

if TYPE_CHECKING:  # annotation-only: config_model imports THIS module at runtime
    from copthief_core.shared.config_model import PheromoneParams

SCENT_MODEL = "scent_model"
DEFAULT_SCENT_MODEL = "subtractive_chebyshev_v1"
# M7-25 (Round-16 settlement with the opponent team): the information-consumption
# posture as a declarable lock family. `belief` is our shipped default — it is the
# posture the frame validator's firewall already enforces in code (PRD_scent §10.1).
INFO_MODE = "info_mode"
DEFAULT_INFO_MODE = "belief"

# Registered param name -> the signed `pheromones` attribute it must equal. Params with
# no signed counterpart (kernel, distance, cadence...) are physics the registration
# pins on its own; App F binds none of them (PRD_scent §9.1).
_SIGNED_OVERLAP: dict[str, dict[str, str]] = {
    "subtractive_chebyshev_v1": {
        "field_size": "grid_size",
        "emit_intensity": "center_intensity",
        "min_center_intensity": "min_center_intensity",
        "decay_per_step": "decay",
    },
    "multiplicative_book_v1": {
        "field_size": "grid_size",
        "center_intensity": "center_intensity",
        "decay_rho": "decay",
    },
}


class LockedModelError(ValueError):
    """The registry is unusable: bad version, unknown registration, or params that
    disagree with the signed constitution."""


@dataclass(frozen=True)
class LockedModelRegistry:
    """The committed registrations, keyed `"<family>:<name>"` (kit SPEC §7)."""

    version: str
    docs: dict[str, dict[str, Any]]

    def doc(self, family: str, name: str) -> dict[str, Any]:
        """The registered doc, or LockedModelError — a lock we cannot name, we cannot play."""
        key = f"{family}:{name}"
        if key not in self.docs:
            raise LockedModelError(f"no registration {key!r}; known: {sorted(self.docs)}")
        return self.docs[key]

    def hash(self, family: str, name: str) -> str:
        """The declared value: `sha256(canonical_json(doc))`, equal to the kit pin."""
        return canonical_hash(self.doc(family, name))

    @staticmethod
    def declared_key(family: str) -> str:
        """The negotiate-extras key that carries the hash — kit SPEC §7 `<family>_sha256`."""
        return f"{family}_sha256"


def load_locked_models(path: Path) -> LockedModelRegistry:
    """Load the committed registry (Input: locked_models.json path; Output: registry;
    Raises: LockedModelError on a version this code does not understand)."""
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    version = str(raw.get("version", ""))
    if not version:
        raise LockedModelError(f"{path} carries no version (CLAUDE.md §1 #9)")
    docs = {str(key): dict(doc) for key, doc in raw["models"].items()}
    return LockedModelRegistry(version=version, docs=docs)


def assert_agrees_with(doc: dict[str, Any], pheromones: PheromoneParams) -> None:
    """Refuse a registration whose params contradict the signed pheromone terms.

    Input: a locked-model doc + the constitution's `PheromoneParams`; Output: None;
    Raises: LockedModelError listing every disagreement. This is the guard that keeps
    the hash we declare and the physics we play the same object.
    """
    name = str(doc["name"])
    overlap = _SIGNED_OVERLAP.get(name, {})
    params = doc["params"]
    problems = [
        f"{param}={params[param]!r} but signed {attribute}={getattr(pheromones, attribute)!r}"
        for param, attribute in overlap.items()
        if param in params and params[param] != getattr(pheromones, attribute)
    ]
    if problems:
        raise LockedModelError(
            f"locked model {name!r} disagrees with the signed constitution: " + "; ".join(problems)
        )


def build_scent_model(
    registry: LockedModelRegistry, name: str, pheromones: PheromoneParams
) -> ScentModel:
    """The ONE door from a registration to running physics (M7-14).

    Input: the committed registry + a model name + the signed pheromone terms;
    Output: the constructed `ScentModel`; Raises: LockedModelError on an unknown name
    or a registration the constitution contradicts. Peer sessions and the referee
    harness both build here, so the hash we declare and the physics we play — in live
    games AND in arena/GA measurements — stay the same object.
    """
    doc = registry.doc(SCENT_MODEL, name)
    assert_agrees_with(doc, pheromones)
    return make_scent_model(name, params=doc["params"])


def lock_decision(ours: str | None, theirs: str | None) -> str:
    """The kit SPEC §7 refusal rule, as its own function because it is BEHAVIOUR, not bytes.

    Refuse only when BOTH peers declare and the hashes differ. Omission is never refusal,
    in either direction — a lock that fail-fasts on a missing declaration cannot start a
    game against the unmodified reference peer, which declares nothing at all. That is a
    self-inflicted forfeit, not a safeguard (ADR-0004 v2 decision 3).
    """
    if ours is not None and theirs is not None and ours != theirs:
        return "refuse"
    return "play"

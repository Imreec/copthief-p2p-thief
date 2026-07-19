"""GA genome (M5-4; HW6 salvage adapted, ADR-0002-logged): a bounded weight vector.

The genome IS a brain's numeric option subset (one gene per configured key, fixed
order). Every operator clips into the per-gene search box, so the search space is
closed — no individual can leave config-declared bounds. Stdlib-only by design.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class GeneSpec:
    """The search box: gene names + per-gene [low, high] bounds (fixed order)."""

    names: tuple[str, ...]
    low: tuple[float, ...]
    high: tuple[float, ...]


def clip(spec: GeneSpec, genome: list[float]) -> list[float]:
    """The genome forced into the search box (shared by every operator)."""
    return [
        min(max(value, lo), hi) for value, lo, hi in zip(genome, spec.low, spec.high, strict=True)
    ]


def random_genome(spec: GeneSpec, rng: random.Random) -> list[float]:
    """A uniform in-box individual."""
    return [rng.uniform(lo, hi) for lo, hi in zip(spec.low, spec.high, strict=True)]


def decode(spec: GeneSpec, genome: list[float]) -> dict[str, float]:
    """Genome vector → brain options mapping (the factory's `options` shape)."""
    return dict(zip(spec.names, genome, strict=True))

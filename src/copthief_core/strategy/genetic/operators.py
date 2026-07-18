"""GA operators (M5-4; HW6 salvage adapted): tournament, blend crossover, mutation.

One `random.Random` threads through everything (the caller's), so a fixed seed
reproduces the run byte-for-byte — the determinism mandate. All outputs are clipped
into the search box.
"""

from __future__ import annotations

import random

from copthief_core.strategy.genetic.genome import GeneSpec, clip

Scored = list[tuple[list[float], float]]


def tournament_select(scored: Scored, size: int, rng: random.Random) -> list[float]:
    """The fittest of `size` uniformly drawn contenders (ties: earliest drawn)."""
    contenders = [scored[rng.randrange(len(scored))] for _ in range(size)]
    return max(contenders, key=lambda pair: pair[1])[0][:]


def blend_crossover(
    spec: GeneSpec, a: list[float], b: list[float], alpha: float, rng: random.Random
) -> list[float]:
    """Per-gene blend: child gene drawn uniformly from the alpha-widened parent span."""
    child = []
    for gene_a, gene_b in zip(a, b, strict=True):
        lo, hi = min(gene_a, gene_b), max(gene_a, gene_b)
        span = hi - lo
        child.append(rng.uniform(lo - alpha * span, hi + alpha * span))
    return clip(spec, child)


def gaussian_mutate(
    spec: GeneSpec, genome: list[float], sigma: float, rate: float, rng: random.Random
) -> list[float]:
    """Each gene perturbed with probability `rate` by N(0, sigma·gene_span)."""
    mutated = []
    for value, lo, hi in zip(genome, spec.low, spec.high, strict=True):
        if rng.random() < rate:
            value += rng.gauss(0.0, sigma * (hi - lo))
        mutated.append(value)
    return clip(spec, mutated)

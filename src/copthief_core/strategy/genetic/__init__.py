"""Offline genetic tuning (M5-4; HW6 salvage adapted, ADR-0002-logged).

Config-driven (`config/ga.json`), stdlib-only, referee-mode-only, role-blind: each
repo evolves its own role brain's weight vector against a fixed reference opponent.
Tuned weights ship as CONFIG (never code) and never deploy to the sparring host.
"""

from copthief_core.strategy.genetic.evolve import EvolutionResult, Generation, evolve
from copthief_core.strategy.genetic.genome import GeneSpec, clip, decode, random_genome
from copthief_core.strategy.genetic.runs import GaConfig, GaPhase, load_ga_config

__all__ = [
    "EvolutionResult",
    "GaConfig",
    "GaPhase",
    "GeneSpec",
    "Generation",
    "__version__",
    "clip",
    "decode",
    "evolve",
    "load_ga_config",
    "random_genome",
]
__version__ = "1.00"

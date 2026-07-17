"""copthief_core.sdk — SimulationSdk, THE single business entry point (guidelines §4).

Every consumer — CLI, GUI, arena, sparring runner, series runner — goes through this
facade; nothing above it touches peer/infra internals directly (PLAN §3).
"""

__all__ = ["__version__"]
__version__ = "1.00"

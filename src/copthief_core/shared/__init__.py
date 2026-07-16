"""copthief_core.shared — cross-cutting base: config loading, App F guard, versioning.

The App F guard (CLAUDE.md §1 #15) lives here because every consumer — negotiation,
startup, per-game config — must refuse an illegal constitution the same way.
"""

__all__ = ["__version__"]
__version__ = "1.00"

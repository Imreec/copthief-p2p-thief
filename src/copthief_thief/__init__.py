"""copthief_thief — the thief agent's brain and role-specific configuration (NOT mirrored).

Role-repo package (M5-3, docs/PRD_thief_brain.md): `ThiefBrain` — region-survival
scoring + articulation trap-awareness + self-mirror deception timing, all knobs
config-owned (`[strategy.thief]` over the `features.DEFAULT_OPTIONS` data table).
Wire role string: ``"thief"`` (book App B). Selected via the book §6.2 dotted
notation `copthief_thief.brain:ThiefBrain`.

`adversary` holds the opponent MODELS this repo tunes against (M7-30 sealing cops).
They are arena instruments, not part of the agent's API, so they stay unexported and
are named the same way every other arena arm is — by their dotted spec.
"""

from copthief_thief.brain import ThiefBrain

__all__ = ["ThiefBrain", "__version__"]
__version__ = "1.00"

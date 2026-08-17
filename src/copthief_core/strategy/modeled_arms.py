"""Modeled-opponent arm registry (M11 part 2) — the factory's league wing.

Split from `brains.py` when the ninth modeled arm pushed the factory past the
150-line rule. One entry per opponent brain we model in the arena; provenance
and fidelity caveats live in each arm's own module docstring (source repo,
HEAD sha, what is observed vs inferred). Imported lazily by `make_brain` —
the arm modules import `BrainBase` from `brains`, so this module must never
be imported at `brains` module scope.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # circular at runtime: arms import BrainBase from brains
    from copthief_core.strategy.brains import BrainBase

__all__ = ["modeled_arm_classes"]


def modeled_arm_classes() -> dict[str, type[BrainBase]]:
    """Config-name -> class for every modeled league opponent (Input: none;
    Output: the registry dict, rebuilt per call — import cost is trivial and
    laziness keeps the brains<->arms import cycle one-directional)."""
    from copthief_core.strategy.anrbj666_cop import Anrbj666CopBrain
    from copthief_core.strategy.anrbj666_thief import Anrbj666ThiefBrain
    from copthief_core.strategy.best2934_cop import Best2934CopBrain
    from copthief_core.strategy.best2934_thief import Best2934ThiefBrain
    from copthief_core.strategy.bestteam_thief import BestteamThiefBrain
    from copthief_core.strategy.hunter_cop import HunterCopBrain
    from copthief_core.strategy.nisyar1_cop import NisYar1CopBrain
    from copthief_core.strategy.nisyar1_thief import NisYar1ThiefBrain
    from copthief_core.strategy.vibecode_cop import VibecodeCopBrain
    from copthief_core.strategy.vibecode_thief import VibecodeThiefBrain

    return {
        "best2934-police": Best2934CopBrain,
        "best2934-thief": Best2934ThiefBrain,
        "bestteam-thief": BestteamThiefBrain,
        "vibecode-police": VibecodeCopBrain,
        "vibecode-thief": VibecodeThiefBrain,
        "hunter-cop": HunterCopBrain,
        "nisyar1-thief": NisYar1ThiefBrain,
        "nisyar1-police": NisYar1CopBrain,
        "anrbj666-police": Anrbj666CopBrain,
        "anrbj666-thief": Anrbj666ThiefBrain,
    }

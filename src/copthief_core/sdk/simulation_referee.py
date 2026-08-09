"""Referee-mode series methods, split from `sdk/simulation` at M7-19 (150-line rule).

The referee seam grew a second door — the capture-claim channel joins the scent-model
and information-feed doors — and `SimulationSdk` crossed the file limit. Split, never
compressed: this mixin owns the two headless-series entry points and nothing else, so
the facade keeps its single-gateway shape (PLAN §3) with one less concern in the file.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from copthief_core.shared.config_model import Constitution
from copthief_core.shared.private_model import PrivateSettings
from copthief_core.strategy.info_feed import BeliefFeed
from copthief_core.strategy.referee import RefereeGameResult
from copthief_core.strategy.scenarios import Scenario, play_referee_series, play_scenario_series

__all__ = ["RefereeSeriesMixin"]


class RefereeSeriesMixin:
    """The headless game sources behind the arena, the DoD floors and the GA.

    Mixed into `SimulationSdk`, which owns these attributes; declared here so the
    methods type-check on their own (`mypy --strict`).
    """

    constitution: Constitution
    private: PrivateSettings

    def referee_series(
        self, police_brain: str, thief_brain: str, *, seeds: list[int]
    ) -> list[RefereeGameResult]:
        """Headless referee-mode series on the canonical signed starts (M3-5/M3-6)."""
        return play_referee_series(
            self.constitution,
            police_brain_name=police_brain,
            thief_brain_name=thief_brain,
            smell_trust=self.private.smell_trust_weight,
            seeds=seeds,
        )

    def scenario_series(
        self,
        *,
        police: str,
        thief: str,
        scenarios: Sequence[Scenario],
        police_options: Mapping[str, float] | None = None,
        thief_options: Mapping[str, float] | None = None,
        belief_feed: BeliefFeed | None = None,
        police_feed: str | None = None,
        thief_feed: str | None = None,
        scent_model: str | None = None,
        claim_threshold: float | None = None,
        thief_claim_feed: str | None = None,
    ) -> list[RefereeGameResult]:
        """Referee-mode series over a start-scenario suite (M5-2) — the arena's and
        the DoD floors' game source; options carry per-brain config knobs, and
        `belief_feed` selects the wire-shape information structure (default hidden).
        M7-14: `scent_model` names the run's physics (resolved against the committed
        registry); `thief_feed` names the thief side's information structure. M7-19:
        `claim_threshold` models the cop's capture-claim channel and `thief_claim_feed`
        is what the thief learns on the turns it declared."""
        return play_scenario_series(
            self.constitution,
            police_brain_name=police,
            thief_brain_name=thief,
            smell_trust=self.private.smell_trust_weight,
            scenarios=scenarios,
            police_options=police_options,
            thief_options=thief_options,
            belief_feed=belief_feed,
            police_feed_name=police_feed,
            thief_feed_name=thief_feed,
            scent_model_name=scent_model,
            locked_models=self.private.locked_models,
            claim_threshold=claim_threshold,
            thief_claim_feed_name=thief_claim_feed,
        )

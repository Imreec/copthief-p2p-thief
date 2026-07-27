"""The GA evolves UNDER the claim policy it will actually play (M7-20).

M7-19 deployed a claim threshold, and M7-18 proved the claim-reading opponent model the
previous retune used (`truth-lag1`) understates a real reader by a full step. Both facts
are invisible to a GA that cannot express them, so fitness could not see either: the
candidate always claimed, and its "claim-reading" sparring partner was a lagged
approximation.

Two knobs close that. `claim_threshold` is run-level (it is a police property, and the
referee applies it to the police side whichever role is being evolved). `claim_feed` is
per opponent, with a run-level fallback — the pool's whole point is a MIXTURE where some
opponents read our claims and others do not.

Role-blind: nothing here names this repo's brain or its shipped values.
"""

from pathlib import Path

from copthief_core.shared.config import load_all
from copthief_core.strategy.genetic.fitness import opponent_fitness
from copthief_core.strategy.genetic.runs import GaConfig, load_ga_config
from copthief_core.strategy.scenarios import scenario_suite

CONSTITUTION, PRIVATE, _LIMITS = load_all(Path("config"), counted=False)
SHIPPED = load_ga_config(Path("config") / "ga.json")


def test_the_claim_knobs_default_to_the_historical_behaviour() -> None:
    # Absent from every shipped GA config => the emitter/physics the old runs measured,
    # so no committed GA artifact is retroactively invalidated by the feature landing.
    assert SHIPPED.claim_threshold is None
    assert SHIPPED.claim_feed is None


def test_a_pool_members_claim_feed_overrides_the_run_level_one() -> None:
    config = GaConfig(
        **{
            **{k: getattr(SHIPPED, k) for k in SHIPPED.__dataclass_fields__},
            "claim_feed": "truth",
        }
    )
    assert config.claim_feed_for({"spec": "ref-thief"}) == "truth"
    assert config.claim_feed_for({"spec": "ref-thief", "claim_feed": None}) is None
    assert config.claim_feed_for({"spec": "belief-evader", "claim_feed": "truth"}) == "truth"


def _chaser_config(threshold: float | None) -> GaConfig:
    """A pure chaser as the candidate: every one of its captures is landing-form, so a
    claim threshold it can never meet must collapse its fitness to zero."""
    fields = {k: getattr(SHIPPED, k) for k in SHIPPED.__dataclass_fields__}
    fields.update(
        role="police",
        brain="greedy-manhattan",
        opponent="random",
        opponent_options={},
        opponent_feed=None,
        opponent_pool=(),
        claim_threshold=threshold,
        claim_feed=None,
    )
    return GaConfig(**fields)


def test_fitness_is_evaluated_under_the_candidates_claim_policy() -> None:
    scenarios = scenario_suite(CONSTITUTION, seeds=[1, 2, 3, 4], min_separation=4)
    opponent = {"spec": "random"}
    loud = opponent_fitness(
        _chaser_config(0.0),
        CONSTITUTION,
        smell_trust=PRIVATE.smell_trust_weight,
        scenarios=scenarios,
        candidate_options={},
        opponent=opponent,
        locked_models=PRIVATE.locked_models,
    )
    silent = opponent_fitness(
        _chaser_config(2.0),  # a probability can never reach 2.0 => never declares
        CONSTITUTION,
        smell_trust=PRIVATE.smell_trust_weight,
        scenarios=scenarios,
        candidate_options={},
        opponent=opponent,
        locked_models=PRIVATE.locked_models,
    )
    assert loud > 0.0  # a chaser lands on its quarry and declares it
    assert silent == 0.0  # the same chaser, forbidden to declare, converts nothing

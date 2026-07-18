"""M3 exit criterion (PLAN §13; PRD_belief §3): the filter beats the baseline, seeded.

Referee-mode simulations — the harness holds the ground truth, walks a seeded legal
opponent, emits its honest locked-model trail, and feeds both trackers the same grids.
The exact Bayes filter must beat the last-known-position tracker on mean belief-error
(primary) across the seed set on the shipped config; argmax-hit-rate is the secondary.
"""

from pathlib import Path

from copthief_core.shared.config import load_all
from copthief_core.strategy.belief_eval import run_belief_trial

CONSTITUTION, PRIVATE, _LIMITS = load_all(Path("config"), counted=False)
SEEDS = range(1, 11)


def _trial(seed: int):  # noqa: ANN202 - shared shorthand
    return run_belief_trial(
        CONSTITUTION,
        smell_trust=PRIVATE.smell_trust_weight,
        seed=seed,
        steps=CONSTITUTION.movement.survival_threshold,
    )


def test_filter_beats_baseline_on_mean_belief_error_across_the_seed_set() -> None:
    results = [_trial(seed) for seed in SEEDS]
    filter_mean = sum(r.filter_mean_error for r in results) / len(results)
    baseline_mean = sum(r.baseline_mean_error for r in results) / len(results)
    assert filter_mean < baseline_mean, (
        f"filter {filter_mean:.4f} must beat baseline {baseline_mean:.4f}"
    )
    # Secondary metric: the filter's argmax lands on the truth more often too.
    filter_hits = sum(r.filter_hit_rate for r in results) / len(results)
    baseline_hits = sum(r.baseline_hit_rate for r in results) / len(results)
    assert filter_hits > baseline_hits


def test_filter_wins_on_every_individual_seed_not_just_on_average() -> None:
    for seed in SEEDS:
        result = _trial(seed)
        assert result.filter_mean_error < result.baseline_mean_error, f"seed {seed}"


def test_trials_are_seed_reproducible() -> None:
    assert _trial(3) == _trial(3)
    assert _trial(3) != _trial(4)

"""Deception-efficacy A/B instrument (TODO M5-6): banks measured against ground truth.

The metric: mean belief-error induced per lie (error_after − error_before over the
referee's truth-anchored trace), split by verdict — computable ONLY in referee mode,
where the harness knows the true thief cell. The series runner is config-driven and
role-blind (PR #29 rule): each repo measures whatever thief its config names.
"""

from pathlib import Path

from copthief_core.sdk.arena_config import load_arena_config
from copthief_core.shared.config import load_all, load_gazetteer
from copthief_core.strategy.deception_eval import BankResult, efficacy, run_bank_series
from copthief_core.strategy.hints import VERDICT_LIE, VERDICT_TRUTH
from copthief_core.strategy.verbal import HintTraceRow

CONSTITUTION, PRIVATE, _LIMITS = load_all(Path("config"), counted=False)
ARENA = load_arena_config(Path("config") / "arena.json")
GAZETTEER = load_gazetteer(
    Path("config") / "gazetteer.json",
    map_area=CONSTITUTION.world.map_area,
    board=CONSTITUTION.board.make_board(),
)


def _row(verdict: str, before: float, after: float, step: int = 1) -> HintTraceRow:
    return HintTraceRow(step=step, verdict=verdict, error_before=before, error_after=after)


def test_efficacy_splits_mean_induced_error_by_verdict() -> None:
    trace = [
        _row(VERDICT_LIE, 0.5, 0.9),
        _row(VERDICT_LIE, 0.5, 0.7),
        _row(VERDICT_TRUTH, 0.5, 0.4),
    ]
    summary = efficacy(trace)
    assert summary.lies == 2
    assert summary.truths == 1
    assert abs(summary.lie_delta - 0.3) < 1e-9
    assert abs(summary.truth_delta - (-0.1)) < 1e-9


def test_efficacy_of_an_empty_trace_is_all_zero() -> None:
    summary = efficacy([])
    assert (summary.lies, summary.truths) == (0, 0)
    assert summary.lie_delta == 0.0
    assert summary.truth_delta == 0.0


def test_bank_series_is_deterministic_and_counts_games() -> None:
    def run() -> list[BankResult]:
        return run_bank_series(
            CONSTITUTION,
            gazetteer=GAZETTEER,
            police_brain_name="greedy-manhattan",
            thief_brain_name="greedy-manhattan",
            smell_trust=PRIVATE.smell_trust_weight,
            hint_trust=PRIVATE.hint_trust_default,
            seeds=[1, 2],
            min_separation=ARENA.scenario_min_separation,
            banks=["classic", "terse"],
        )

    first = run()
    assert first == run()
    assert [r.bank for r in first] == ["classic", "terse"]
    for result in first:
        assert result.games == 2
        assert result.summary.lies == 0  # core baselines never lie
        assert result.summary.truths > 0  # every turn still talks (truthful default)

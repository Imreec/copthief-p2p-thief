"""Deception-efficacy A/B instrument (TODO M5-6; PRD_thief_brain §3 M5-6 seam).

Measures what a template bank's hints DO to the tracking belief, per verdict, over
a seeded scenario series — referee mode only, where the harness holds ground truth
(the metric is meaningless anywhere else). Role-blind and config-driven (PR #29
rule): each repo measures whatever thief its own config names; the committed table
ships the winning bank into `[strategy] hint_bank`.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from copthief_core.domain.gazetteer import Gazetteer
from copthief_core.domain.rules import Outcome
from copthief_core.shared.config_model import Constitution
from copthief_core.strategy.brains import make_brain
from copthief_core.strategy.hints import VERDICT_LIE
from copthief_core.strategy.referee import play_referee_game
from copthief_core.strategy.scenarios import scenario_suite
from copthief_core.strategy.verbal import HintTraceRow


@dataclass(frozen=True)
class EfficacySummary:
    """Mean induced belief error per verdict (positive = the hint hurt the tracker)."""

    lies: int
    truths: int
    lie_delta: float
    truth_delta: float


def efficacy(trace: Iterable[HintTraceRow]) -> EfficacySummary:
    """Summarize a truth-anchored hint trace by sealed verdict."""
    lie_deltas: list[float] = []
    truth_deltas: list[float] = []
    for row in trace:
        delta = row.error_after - row.error_before
        (lie_deltas if row.verdict == VERDICT_LIE else truth_deltas).append(delta)
    return EfficacySummary(
        lies=len(lie_deltas),
        truths=len(truth_deltas),
        lie_delta=sum(lie_deltas) / len(lie_deltas) if lie_deltas else 0.0,
        truth_delta=sum(truth_deltas) / len(truth_deltas) if truth_deltas else 0.0,
    )


@dataclass(frozen=True)
class BankResult:
    """One bank's measured A/B row over the full scenario series."""

    bank: str
    games: int
    thief_wins: int
    summary: EfficacySummary


def run_bank_series(
    constitution: Constitution,
    *,
    gazetteer: Gazetteer,
    police_brain_name: str,
    thief_brain_name: str,
    smell_trust: float,
    hint_trust: float,
    seeds: Iterable[int],
    min_separation: int,
    banks: Iterable[str],
    police_options: Mapping[str, float] | None = None,
    thief_options: Mapping[str, float] | None = None,
) -> list[BankResult]:
    """A/B the banks over one seeded scenario suite (fresh brains per game; two RNG
    streams per seed, police 2n / thief 2n+1 — the scenarios.py discipline)."""
    suite = scenario_suite(constitution, seeds=list(seeds), min_separation=min_separation)
    results: list[BankResult] = []
    for bank in banks:
        trace: list[HintTraceRow] = []
        wins = 0
        for scenario in suite:
            outcome = play_referee_game(
                constitution,
                police_brain=make_brain(
                    police_brain_name, seed=2 * scenario.seed, options=police_options
                ),
                thief_brain=make_brain(
                    thief_brain_name, seed=2 * scenario.seed + 1, options=thief_options
                ),
                smell_trust=smell_trust,
                seed=scenario.seed,
                cop_start=scenario.cop_start,
                thief_start=scenario.thief_start,
                gazetteer=gazetteer,
                hint_bank=bank,
                hint_trust=hint_trust,
                verbal_trace=trace,
            ).outcome
            wins += outcome is Outcome.THIEF_SURVIVAL
        results.append(
            BankResult(bank=bank, games=len(suite), thief_wins=wins, summary=efficacy(trace))
        )
    return results

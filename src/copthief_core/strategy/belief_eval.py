"""Referee-mode belief evaluation (PRD_belief §3; PLAN §13 M3 exit criterion).

The harness holds ground truth: a seeded opponent walks legal moves, honestly emits
its locked-model trail (deposit-after-move → decay → snapshot, SQ1), and both
trackers consume the same transmitted grids blind. Per-step belief-error
(`1 - P(truth)`) and argmax hits are averaged per trial; the integration suite and
`scripts/belief_eval.py` (the committed evidence table) both run through here.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from copthief_core.domain.belief import BeliefFilter, LastKnownTracker
from copthief_core.domain.rules import legal_moves
from copthief_core.domain.scent import ScentField
from copthief_core.shared.config_model import Constitution


@dataclass(frozen=True)
class TrialResult:
    """One seeded referee-mode trial's aggregate metrics (both trackers, same grids)."""

    seed: int
    steps: int
    filter_mean_error: float
    baseline_mean_error: float
    filter_hit_rate: float
    baseline_hit_rate: float


def run_belief_trial(
    constitution: Constitution, *, smell_trust: float, seed: int, steps: int
) -> TrialResult:
    """Walk a seeded legal opponent for `steps` turns and score both trackers.

    Input: the signed constitution + the private trust weight + seed/length;
    Output: per-trial mean belief-errors and argmax-hit rates. Deterministic per seed.
    """
    board = constitution.board.make_board()
    pheromones = constitution.pheromones
    move_set = constitution.movement.move_set
    rng = random.Random(seed)
    truth = constitution.board.thief_start
    trail = ScentField(
        board_size=constitution.board.grid_size,
        window=pheromones.grid_size,
        decay=pheromones.decay,
        min_center_intensity=pheromones.min_center_intensity,
        origin=constitution.board.axis_start_index,
    )
    bayes = BeliefFilter(
        board=board,
        move_set=move_set,
        start=truth,
        center_intensity=pheromones.center_intensity,
        decay=pheromones.decay,
        smell_trust=smell_trust,
        hint_trust=0.0,  # no hints in this trial: scent-only evaluation (M3-3 scope)
    )
    baseline = LastKnownTracker(board=board, start=truth)
    filter_errors: list[float] = []
    baseline_errors: list[float] = []
    filter_hits = 0
    baseline_hits = 0
    for _ in range(steps):
        move = rng.choice(sorted(legal_moves(board, truth, move_set)))
        truth = board.apply_move(truth, move)
        # SQ1 honest emission: deposit at the NEW position, decay once, transmit.
        trail.deposit(truth, pheromones.center_intensity)
        trail.decay()
        grid = trail.snapshot()
        for tracker in (bayes, baseline):
            tracker.predict()
            tracker.update_scent(grid)
        filter_errors.append(bayes.belief_error(truth))
        baseline_errors.append(baseline.belief_error(truth))
        filter_hits += bayes.argmax() == truth
        baseline_hits += baseline.argmax() == truth
    return TrialResult(
        seed=seed,
        steps=steps,
        filter_mean_error=sum(filter_errors) / steps,
        baseline_mean_error=sum(baseline_errors) / steps,
        filter_hit_rate=filter_hits / steps,
        baseline_hit_rate=baseline_hits / steps,
    )

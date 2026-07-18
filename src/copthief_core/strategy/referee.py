"""Referee-mode headless games (TODO M3-5; PLAN §3 "one rules module, two modes").

The harness holds ground truth and resolves endings with `rules.check_end` (all three
capture forms). Information stays peer-symmetric for the BRAINS — each side sees only
its own truth plus a belief fed by the opponent's honest locked-model trail (SQ1
emission), exactly what the wire would carry. The thief moves first (F2); its
threshold move ends the game as survival before the cop replies (wire-mirrored).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import Coord
from copthief_core.domain.rules import Outcome, check_end
from copthief_core.domain.scent import ScentField
from copthief_core.shared.config_model import Constitution
from copthief_core.strategy.brains import BrainBase, Observation, make_brain


@dataclass(frozen=True)
class RefereeGameResult:
    """One headless mini-game's observed ending."""

    seed: int
    outcome: Outcome
    steps: int


def _belief(constitution: Constitution, *, start: Coord, smell_trust: float) -> BeliefFilter:
    return BeliefFilter(
        board=constitution.board.make_board(),
        move_set=constitution.movement.move_set,
        start=start,
        center_intensity=constitution.pheromones.center_intensity,
        decay=constitution.pheromones.decay,
        smell_trust=smell_trust,
        hint_trust=0.0,  # hints are a peer-mode feature; referee trials are scent-only
    )


def _trail(constitution: Constitution) -> ScentField:
    return ScentField(
        board_size=constitution.board.grid_size,
        window=constitution.pheromones.grid_size,
        decay=constitution.pheromones.decay,
        min_center_intensity=constitution.pheromones.min_center_intensity,
        origin=constitution.board.axis_start_index,
    )


def play_referee_game(
    constitution: Constitution,
    *,
    police_brain: BrainBase,
    thief_brain: BrainBase,
    smell_trust: float,
    seed: int,
) -> RefereeGameResult:
    """One full-information-resolved, belief-driven mini-game (Input: constitution +
    two brains + trust + the bookkeeping seed; Output: the observed ending)."""
    board = constitution.board.make_board()
    move_set = constitution.movement.move_set
    threshold = constitution.movement.survival_threshold
    max_moves = constitution.movement.max_moves
    intensity = constitution.pheromones.center_intensity
    cop, thief = constitution.board.cop_start, constitution.board.thief_start
    police_belief = _belief(constitution, start=thief, smell_trust=smell_trust)
    thief_belief = _belief(constitution, start=cop, smell_trust=smell_trust)
    thief_trail, cop_trail = _trail(constitution), _trail(constitution)

    def ended(steps_survived: int) -> Outcome | None:
        return check_end(
            board,
            cop_pos=cop,
            thief_pos=thief,
            steps_survived=steps_survived,
            survival_threshold=threshold,
            max_moves=max_moves,
        )

    for step in range(1, min(threshold, max_moves) + 1):
        thief = board.apply_move(
            thief,
            thief_brain.pick_move(
                Observation(
                    board=board, position=thief, move_set=move_set, role="thief", step=step
                ),
                thief_belief,
            ),
        )
        thief_trail.deposit(thief, intensity)
        thief_trail.decay()
        police_belief.predict()
        police_belief.update_scent(thief_trail.snapshot())
        outcome = ended(step)
        if outcome is not None:
            return RefereeGameResult(seed=seed, outcome=outcome, steps=step)
        cop = board.apply_move(
            cop,
            police_brain.pick_move(
                Observation(board=board, position=cop, move_set=move_set, role="police", step=step),
                police_belief,
            ),
        )
        cop_trail.deposit(cop, intensity)
        cop_trail.decay()
        thief_belief.predict()
        thief_belief.update_scent(cop_trail.snapshot())
        outcome = ended(step)
        if outcome is not None:
            return RefereeGameResult(seed=seed, outcome=outcome, steps=step)
    return RefereeGameResult(  # unreachable in practice: the threshold check fires in-loop
        seed=seed, outcome=Outcome.THIEF_SURVIVAL, steps=min(threshold, max_moves)
    )


def play_referee_series(
    constitution: Constitution,
    *,
    police_brain_name: str,
    thief_brain_name: str,
    smell_trust: float,
    seeds: Iterable[int],
) -> list[RefereeGameResult]:
    """A headless seeded series: fresh brains/beliefs per game, two RNG streams per
    seed (police 2n, thief 2n+1) so pairings never share a stream."""
    return [
        play_referee_game(
            constitution,
            police_brain=make_brain(police_brain_name, seed=2 * seed),
            thief_brain=make_brain(thief_brain_name, seed=2 * seed + 1),
            smell_trust=smell_trust,
            seed=seed,
        )
        for seed in seeds
    ]

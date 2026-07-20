"""Referee-mode headless games (TODO M3-5/M5-2; PLAN §3 "one rules module, two modes").

The harness holds ground truth and resolves endings with `rules.check_end` (all three
capture forms). Information stays peer-symmetric for the BRAINS — each side sees only
its own truth plus a belief fed by the opponent's honest locked-model trail (SQ1
emission), exactly what the wire would carry. The thief moves first (F2); its
threshold move ends the game as survival before the cop replies (wire-mirrored).
M5-2: the cop turn applies a full `Decision` — a barrier joins the board AND both
belief filters, and the cop forgoes its step (reference BARRIER semantics).
"""

from __future__ import annotations

from dataclasses import dataclass

from copthief_core.domain.board import Coord
from copthief_core.domain.gazetteer import Gazetteer
from copthief_core.domain.rules import Outcome, check_end
from copthief_core.shared.config_model import Constitution
from copthief_core.strategy.brains import BrainBase, Observation
from copthief_core.strategy.info_feed import BeliefFeed, ScentFeed
from copthief_core.strategy.referee_setup import referee_belief, referee_trail
from copthief_core.strategy.verbal import HintTraceRow, apply_thief_hint


@dataclass(frozen=True)
class RefereeGameResult:
    """One headless mini-game's observed ending."""

    seed: int
    outcome: Outcome
    steps: int
    barriers_placed: int = 0


def play_referee_game(
    constitution: Constitution,
    *,
    police_brain: BrainBase,
    thief_brain: BrainBase,
    smell_trust: float,
    seed: int,
    cop_start: Coord | None = None,
    thief_start: Coord | None = None,
    gazetteer: Gazetteer | None = None,
    hint_bank: str = "",
    hint_trust: float = 0.0,
    verbal_trace: list[HintTraceRow] | None = None,
    belief_feed: BeliefFeed | None = None,
) -> RefereeGameResult:
    """One full-information-resolved, belief-driven mini-game (Input: constitution +
    two brains + trust + the bookkeeping seed + optional scenario starts; Output: the
    observed ending)."""
    board = constitution.board.make_board()
    move_set = constitution.movement.move_set
    threshold = constitution.movement.survival_threshold
    max_moves = constitution.movement.max_moves
    max_barriers = constitution.movement.max_barriers
    intensity = constitution.pheromones.center_intensity
    cop = constitution.board.cop_start if cop_start is None else cop_start
    thief = constitution.board.thief_start if thief_start is None else thief_start
    police_belief = referee_belief(
        constitution, start=thief, smell_trust=smell_trust, hint_trust=hint_trust
    )
    thief_belief = referee_belief(constitution, start=cop, smell_trust=smell_trust)
    thief_trail, cop_trail = referee_trail(constitution), referee_trail(constitution)
    feed = ScentFeed() if belief_feed is None else belief_feed  # wire-shape seam

    def result(outcome: Outcome, steps: int) -> RefereeGameResult:
        return RefereeGameResult(
            seed=seed, outcome=outcome, steps=steps, barriers_placed=len(board.barriers)
        )

    for step in range(1, min(threshold, max_moves) + 1):
        thief_decision = thief_brain.decide(
            Observation(
                board=board,
                position=thief,
                move_set=move_set,
                role="thief",
                step=step,
                survival_threshold=threshold,
                max_moves=max_moves,
                gazetteer=gazetteer,
                own_smell=thief_trail.snapshot(),
                pheromones=constitution.pheromones,
            ),
            thief_belief,
        )
        thief = board.apply_move(thief, thief_decision.move)
        thief_trail.advance(thief, intensity)
        police_belief = feed.observe(police_belief, trail=thief_trail, truth=thief, board=board)
        if gazetteer is not None:  # M5-6: the verbal layer, peer-order (scent→hint)
            apply_thief_hint(
                gazetteer,
                decision=thief_decision,
                truth=thief,
                belief=police_belief,
                max_words=constitution.world.hint_max_words,
                salt=step,
                bank=hint_bank,
                trace=verbal_trace,
            )
        outcome = check_end(
            board,
            cop_pos=cop,
            thief_pos=thief,
            steps_survived=step,
            survival_threshold=threshold,
            max_moves=max_moves,
        )
        if outcome is not None:
            return result(outcome, step)
        decision = police_brain.decide(
            Observation(
                board=board,
                position=cop,
                move_set=move_set,
                role="police",
                step=step,
                barriers_used=len(board.barriers),
                max_barriers=max_barriers,
                survival_threshold=threshold,
                max_moves=max_moves,
                own_smell=cop_trail.snapshot(),
                pheromones=constitution.pheromones,
            ),
            police_belief,
        )
        if decision.barrier is not None:  # the cop walls instead of stepping
            board = board.with_barrier(decision.barrier)
            police_belief.note_barrier(decision.barrier)
            thief_belief.note_barrier(decision.barrier)
        else:
            cop = board.apply_move(cop, decision.move)
        cop_trail.advance(cop, intensity)
        thief_belief = feed.observe(thief_belief, trail=cop_trail, truth=cop, board=board)
        outcome = check_end(
            board,
            cop_pos=cop,
            thief_pos=thief,
            steps_survived=step,
            survival_threshold=threshold,
            max_moves=max_moves,
        )
        if outcome is not None:
            return result(outcome, step)
    return result(Outcome.THIEF_SURVIVAL, min(threshold, max_moves))

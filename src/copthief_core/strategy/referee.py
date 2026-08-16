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
from copthief_core.domain.scent_models import ScentModel
from copthief_core.shared.config_model import Constitution
from copthief_core.strategy.brains import BrainBase
from copthief_core.strategy.info_feed import BeliefFeed, ScentFeed
from copthief_core.strategy.referee_claims import ClaimPolicy
from copthief_core.strategy.referee_obs import police_observation, thief_observation
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
    thief_belief_feed: BeliefFeed | None = None,
    thief_claim_feed: BeliefFeed | None = None,
    scent_model: ScentModel | None = None,
    claim_policy: ClaimPolicy | None = None,
) -> RefereeGameResult:
    """One full-information-resolved, belief-driven mini-game (Input: constitution +
    two brains + trust + the bookkeeping seed + optional scenario starts; Output: the
    observed ending). `scent_model` switches the WHOLE world's physics (both trails +
    both observation models, M7-14); `thief_belief_feed` lets the thief's information
    structure differ from the cop's (defaults to `belief_feed` — the balance study's
    symmetric shape unchanged)."""
    board = constitution.board.make_board()
    threshold = constitution.movement.survival_threshold
    max_moves = constitution.movement.max_moves
    intensity = constitution.pheromones.center_intensity
    cop = constitution.board.cop_start if cop_start is None else cop_start
    thief = constitution.board.thief_start if thief_start is None else thief_start
    police_belief = referee_belief(
        constitution,
        start=thief,
        smell_trust=smell_trust,
        hint_trust=hint_trust,
        scent_model=scent_model,
    )
    thief_belief = referee_belief(
        constitution, start=cop, smell_trust=smell_trust, scent_model=scent_model
    )
    thief_trail = referee_trail(constitution, model=scent_model)
    cop_trail = referee_trail(constitution, model=scent_model)
    feed = ScentFeed() if belief_feed is None else belief_feed  # wire-shape seam
    thief_feed = feed if thief_belief_feed is None else thief_belief_feed
    # M7-19: the cop's claim is a strategy choice. M13 (ADR-0016): a claim is graded
    # ONCE, at the thief's receive, against its post-move cell — so it gates ONLY the
    # cop's own landing check below. Unmodelled (the default) = the always-claim
    # emitter; the landing form still requires the cop to be the one who landed.
    claims = ClaimPolicy() if claim_policy is None else claim_policy

    def result(outcome: Outcome, steps: int) -> RefereeGameResult:
        return RefereeGameResult(
            seed=seed, outcome=outcome, steps=steps, barriers_placed=len(board.barriers)
        )

    for step in range(1, min(threshold, max_moves) + 1):
        thief_decision = thief_brain.decide(
            thief_observation(
                constitution,
                board=board,
                position=thief,
                step=step,
                trail=thief_trail,
                gazetteer=gazetteer,
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
            # M13 wire-true (ADR-0016): nothing on the wire grades a thief-initiated
            # collision — the landing form lives on the cop half-turn only. Barrier
            # and imprisonment forms (rules 46/47) remain live here.
            claim_standing=False,
        )
        if outcome is not None:
            return result(outcome, step)
        decision = police_brain.decide(
            police_observation(constitution, board=board, position=cop, step=step, trail=cop_trail),
            police_belief,
        )
        if decision.barrier is not None:  # the cop walls instead of stepping
            board = board.with_barrier(decision.barrier)
            police_belief.note_barrier(decision.barrier)
            thief_belief.note_barrier(decision.barrier)
        else:
            cop = board.apply_move(cop, decision.move)
        # The claim decision, read off the belief as it stands after the thief moved:
        # "how likely is it that I just landed on them". M13 (ADR-0016): it gates only
        # the landing check immediately below — the wire grades a claim once, at the
        # thief's receive, and nothing re-grades it after the thief's next move.
        claims_this_landing = claims.claims(
            barrier_placed=decision.barrier is not None,
            move=decision.move,
            # M13 (ADR-0016): the brain's own landing price when it offers one — the
            # same coupling the live emitter runs (peer/turns.py); raw-belief fallback.
            confidence=(
                decision.landing_confidence
                if decision.landing_confidence is not None
                else police_belief.prob_at(cop)
            ),
        )
        cop_trail.advance(cop, intensity)
        # Claim-conditional information (PRD_claims §5.2), composed at the loop level so
        # the BeliefFeed Protocol never learns about claims: a declared cell is a
        # certainty delta, silence leaves the thief on its ordinary hidden channel.
        turn_feed = thief_claim_feed if (claims_this_landing and thief_claim_feed) else thief_feed
        thief_belief = turn_feed.observe(thief_belief, trail=cop_trail, truth=cop, board=board)
        outcome = check_end(
            board,
            cop_pos=cop,
            thief_pos=thief,
            steps_survived=step,
            survival_threshold=threshold,
            max_moves=max_moves,
            claim_standing=claims_this_landing,
        )
        if outcome is not None:
            return result(outcome, step)
    return result(Outcome.THIEF_SURVIVAL, min(threshold, max_moves))

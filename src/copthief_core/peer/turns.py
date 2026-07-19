"""Outbound turn cycle of a PeerSession (PLAN §5), split from session.py (150-line
rule; the inbound half lives in peer/inbound since M5-2).

Mirrors the reference's turn_sender/turn_handler split (oracle sha 960499fd). The SQ1
scent order is wired here: the mover deposits AFTER applying its move at the NEW
position, the own trail decays ONCE, and the snapshot rides the outbound message —
including STAY turns and the mandatory final caught message (the reference's send()
path deposits unconditionally). The receiver absorbs the inbound grid into its known
field, then decays it once per received message.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from copthief_core.domain.state_machine import GameState
from copthief_core.peer.sealing import seal_turn
from copthief_core.strategy.brains import Observation
from copthief_core.strategy.decision import BARRIER_MOVE
from copthief_core.strategy.hints import VERDICT_TRUTH, compose_hint
from copthief_core.wire.turn import TurnMessage

if TYPE_CHECKING:  # annotation-only: the session imports THIS module at runtime
    from copthief_core.peer.session import PeerSession

# The mandatory "you got me" final message (fixed protocol text, mirrors the reference).
FINAL_CAUGHT_HINT = "You got me."


def take_turn(session: PeerSession, *, now: float) -> dict[str, Any]:
    """Pick → seal → deposit scent → build the outbound TurnMessage; nonce withheld."""
    if session.machine.state is GameState.WAITING_FOR_OPPONENT:
        session.machine.advance(GameState.COMPUTING_MOVE)
    verdict = VERDICT_TRUTH
    barrier = None
    response_seconds = 0.0  # the mandatory final message costs no decision time
    if session.caught:  # the mandatory final message: no move, honest answer
        move, hint = "STAY", FINAL_CAUGHT_HINT
    else:
        # M3-5/M5-2: the brain reads OUR truth + the belief — never the opponent's.
        # M5-3 deception kit: gazetteer + our own transmitted trail + signed params.
        decision_started = time.perf_counter()
        decision = session.brain.decide(
            Observation(
                board=session.board,
                position=session.position,
                move_set=session.constitution.movement.move_set,
                role=session.role,
                step=len(session.records) + 1,
                barriers_used=session.barriers_placed,
                max_barriers=session.constitution.movement.max_barriers,
                survival_threshold=session.constitution.movement.survival_threshold,
                max_moves=session.constitution.movement.max_moves,
                gazetteer=session.gazetteer,
                own_smell=session.own_trail.snapshot(),
                pheromones=session.constitution.pheromones,
            ),
            session.belief,
        )
        # Sealed timing (M6-3): decision wall-time, precision mirrors the reference.
        response_seconds = round(time.perf_counter() - decision_started, 3)
        if decision.barrier is not None:  # the police walls instead of stepping
            barrier, move = decision.barrier, BARRIER_MOVE
            session.board = session.board.with_barrier(barrier)
            session.belief.note_barrier(barrier)  # it constrains the thief too
            session.barriers_placed += 1
        else:
            move = decision.move
            session.position = session.board.apply_move(session.position, move)
        max_words = session.constitution.world.hint_max_words
        if session.gazetteer is None:  # M1 fallback bank (no geography for the area)
            hint = session.policy.next_hint(hint_max_words=max_words)
        else:  # M3-4 composer; M5-3: the brain's hint-intent seam decides the timing
            composed = compose_hint(
                session.gazetteer,
                position=session.position,
                max_words=max_words,
                salt=len(session.records),
                verdict=decision.hint_verdict or VERDICT_TRUTH,
                landmark=decision.hint_landmark,
                bank=session.private.hint_bank,  # M5-6: the A/B-shipped bank
            )
            hint, verdict = composed.text, composed.verdict
    step = len(session.records) + 1
    sealed = seal_turn(
        step=step,
        grid_size=session.constitution.board.grid_size,
        position=session.position,
        barriers=session.board.barriers,
        move=move,
        intent=verdict,
        hint=hint,
        # M6-3 token accounting: the template path charges 0 every step; an LLM
        # seam would report its per-call usage here (session.tokens_total ledger).
        model=session.private.llm_model,
        tokens_step=0,
        tokens_total=session.tokens_total,
        response_seconds=response_seconds,
    )
    session.records.append(sealed)
    # SQ1: deposit after the move at the NEW position, then decay the whole trail once.
    session.own_trail.deposit(session.position, session.constitution.pheromones.center_intensity)
    session.own_trail.decay()
    session.machine.advance(GameState.COMMITTING)
    session.machine.advance(GameState.AWAITING_REVEAL)
    message = TurnMessage(
        step=step,
        sender=session.role,
        hint=hint,
        smell_grid=session.own_trail.snapshot(),
        commit=sealed.commit,
        # F5: ISO-8601 UTC string from the caller epoch — no clock read here.
        timestamp=datetime.fromtimestamp(now, UTC).isoformat(),
        # SQ2: the police claims its landing cell on every MOVING turn — free,
        # automatic; STAY and BARRIER claim nothing (MoveType.MOVE-only claims).
        capture_claim=(
            session.position
            if session.role == "police" and move not in ("STAY", BARRIER_MOVE)
            else None
        ),
        barrier_placed=barrier,
        claim_response=session.pending_claim_response,
        win_claim=_win_claim(session, step),
    ).to_wire()
    session.pending_claim_response = None
    if session.caught:
        session.outcome = "cop_capture"
        session.machine.advance(GameState.VERIFYING)
        session.machine.advance(GameState.GAME_OVER)
    return message


def _win_claim(session: PeerSession, step: int) -> dict[str, Any] | None:
    """The thief's survival claim on its threshold turn (never when caught) — F2."""
    threshold = session.constitution.movement.survival_threshold
    if session.role == "thief" and not session.caught and step >= threshold:
        session.outcome = "thief_survival"
        session.machine.advance(GameState.VERIFYING)
        session.machine.advance(GameState.GAME_OVER)
        return {"type": "survival"}
    return None

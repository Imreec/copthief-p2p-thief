"""Turn cycle of a PeerSession (PLAN §5), split from session.py (150-line rule).

Mirrors the reference's turn_sender/turn_handler split (oracle sha 960499fd). The SQ1
scent order is wired here: the mover deposits AFTER applying its move at the NEW
position, the own trail decays ONCE, and the snapshot rides the outbound message —
including STAY turns and the mandatory final caught message (the reference's send()
path deposits unconditionally). The receiver absorbs the inbound grid into its known
field, then decays it once per received message.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from copthief_core.domain.state_machine import GameState
from copthief_core.peer.sealing import seal_turn
from copthief_core.strategy.brains import Observation
from copthief_core.strategy.hints import VERDICT_TRUTH, compose_hint
from copthief_core.wire.turn import TurnMessage
from copthief_core.wire.validation import WireValidationError

if TYPE_CHECKING:  # annotation-only: the session imports THIS module at runtime
    from copthief_core.peer.session import PeerSession

# The mandatory "you got me" final message (fixed protocol text, mirrors the reference).
FINAL_CAUGHT_HINT = "You got me."


def take_turn(session: PeerSession, *, now: float) -> dict[str, Any]:
    """Pick → seal → deposit scent → build the outbound TurnMessage; nonce withheld."""
    if session.machine.state is GameState.WAITING_FOR_OPPONENT:
        session.machine.advance(GameState.COMPUTING_MOVE)
    verdict = VERDICT_TRUTH
    if session.caught:  # the mandatory final message: no move, honest answer
        move, hint = "STAY", FINAL_CAUGHT_HINT
    else:
        # M3-5: the brain reads OUR truth + the belief — never the opponent's truth.
        move = session.brain.pick_move(
            Observation(
                board=session.board,
                position=session.position,
                move_set=session.constitution.movement.move_set,
                role=session.role,
                step=len(session.records) + 1,
            ),
            session.belief,
        )
        session.position = session.board.apply_move(session.position, move)
        max_words = session.constitution.world.hint_max_words
        if session.gazetteer is None:  # M1 fallback bank (no geography for the area)
            hint = session.policy.next_hint(hint_max_words=max_words)
        else:  # M3-4: template×landmark composer; truthful by default (timing = M5)
            composed = compose_hint(
                session.gazetteer,
                position=session.position,
                max_words=max_words,
                salt=len(session.records),
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
        # automatic; STAY claims nothing (mirrors MoveType.MOVE-only claims).
        capture_claim=session.position if session.role == "police" and move != "STAY" else None,
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


def handle_receive_turn(session: PeerSession, raw: dict[str, Any]) -> dict[str, Any]:
    """Validate the inbound turn BEFORE any state change; then advance the machine."""
    try:
        message = TurnMessage.from_wire(raw)
    except WireValidationError as error:
        raise session.collapse(str(error)) from error
    expected = len(session.inbound) + 1
    if message.step != expected:
        raise session.collapse(f"step discontinuity: expected {expected}, got {message.step}")
    session.inbound.append(message)
    # F9: a declared barrier is sealed/audited evidence — it constrains OUR OWN move
    # legality (the M2 gap) and the belief motion model, before anything else reads it.
    if message.barrier_placed is not None:
        barrier = (message.barrier_placed[0], message.barrier_placed[1])
        session.board = session.board.with_barrier(barrier)
        session.belief.note_barrier(barrier)
    # PRD_belief §4 pipeline (reference order): predict, then sharpen with the scent.
    session.belief.predict()
    session.belief.update_scent(message.smell_grid)
    # M3-4: their hint feeds the belief ONLY through the closed-vocabulary parser —
    # adversarial text maps to a known landmark or to nothing (injection-safe by shape).
    if session.gazetteer is not None:
        landmark = session.gazetteer.parse(
            message.hint, max_words=session.constitution.world.hint_max_words
        )
        if landmark is not None:
            session.belief.update_hint(session.gazetteer.cells_for(landmark))
    # SQ1 receive side: absorb their transmitted trail, then one per-message decay.
    session.known_field.absorb(message.smell_grid)
    session.known_field.decay()
    if message.capture_claim is not None:  # SQ2: answer honestly on our next turn
        session.caught = tuple(message.capture_claim) == tuple(session.position)
        session.pending_claim_response = {
            "claim": list(message.capture_claim),
            "caught": session.caught,
        }
    if session.machine.state is GameState.WAITING_FOR_OPPONENT:
        session.machine.advance(GameState.COMPUTING_MOVE)
    elif session.machine.state is GameState.AWAITING_REVEAL:
        session.machine.advance(GameState.VERIFYING)
        if message.claim_response is not None and message.claim_response.get("caught"):
            session.outcome = "cop_capture"  # their honest answer; audit re-proves it
            session.machine.advance(GameState.GAME_OVER)
        elif message.win_claim is not None:
            session.outcome = "thief_survival"  # cross-checked at audit (threshold)
            session.machine.advance(GameState.GAME_OVER)
        else:
            session.machine.advance(GameState.WAITING_FOR_OPPONENT)
    else:
        raise session.collapse(f"turn arrived in state {session.machine.state.name}")
    return {"status": "ok", "step": message.step}

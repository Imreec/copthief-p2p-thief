"""Inbound turn handling, split from peer/turns (150-line rule at M5-2).

The receive half of the reference's turn_sender/turn_handler mirror: validate BEFORE
any state change (adversarial input), fold declared barriers into board + belief (F9),
run the PRD_belief §4 pipeline, absorb the transmitted trail (SQ1 receive side), answer
capture claims honestly (SQ2), and advance the machine.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from copthief_core.domain.state_machine import GameState
from copthief_core.wire.turn import TurnMessage
from copthief_core.wire.validation import WireValidationError

if TYPE_CHECKING:  # annotation-only: the session imports THIS module at runtime
    from copthief_core.peer.session import PeerSession


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

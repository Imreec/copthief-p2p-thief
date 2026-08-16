"""Inbound turn handling, split from peer/turns (150-line rule at M5-2).

The receive half of the reference's turn_sender/turn_handler mirror: validate BEFORE
any state change (adversarial input), fold declared barriers into board + belief (F9),
run the PRD_belief §4 pipeline, absorb the transmitted trail (SQ1 receive side), answer
capture claims honestly (SQ2), and advance the machine.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from copthief_core.domain.rules import is_imprisoned
from copthief_core.domain.scent_frame import frame_explained
from copthief_core.domain.state_machine import GameState
from copthief_core.peer import inbox_order
from copthief_core.wire.turn import TurnMessage
from copthief_core.wire.validation import WireValidationError

if TYPE_CHECKING:  # annotation-only: the session imports THIS module at runtime
    from copthief_core.peer.session import PeerSession


def _tolerated(step: int, disposition: str) -> dict[str, Any]:
    """The ack for a message the transport layer absorbed (M7-8).

    `status` stays "ok" on purpose: a redelivery is not an error to report back — the
    sender did nothing wrong, and answering anything else would make an honest retry
    look like a protocol failure. The caller reads `disposition` to know that nothing
    advanced, so our turn deadline is NOT renewed.
    """
    return {"status": "ok", "step": step, "disposition": disposition}


def _is_opening_handover(session: PeerSession, raw: dict[str, Any]) -> bool:
    """Is this the opponent's opening nil turn? (M7-53)

    Input: the session and the RAW frame — this is decided before `TurnMessage`
    validation, because a handover carries no commit, hint, smell grid or timestamp and
    would be rejected as a malformed game turn on its way past.
    Output: True only for a step-0 frame arriving before any real turn, at most once.

    Keyed on the step ALONE. Their nil turn's field set is theirs to choose, and a
    tolerance that guessed at its shape would break the first time they added a field.
    """
    if session.inbound or session.sequencer.handover_seen:
        return False
    try:
        return int(raw.get("step", -1)) == 0
    except (TypeError, ValueError):
        return False


def handle_receive_turn(session: PeerSession, raw: dict[str, Any]) -> dict[str, Any]:
    """Validate the inbound turn BEFORE any state change; then advance the machine."""
    # M7-53: absorbed ahead of validation and of the sequencer. It is not a game step:
    # nothing is sealed, the belief does not move, the machine does not advance, and
    # the step we await is unchanged — so their first REAL move still lands as step 1.
    if _is_opening_handover(session, raw):
        session.sequencer.handover_seen = True
        return _tolerated(0, inbox_order.HANDOVER)
    try:
        message = TurnMessage.from_wire(raw)
    except WireValidationError as error:
        raise session.collapse(str(error)) from error
    expected = len(session.inbound) + 1
    # Terminal-message step convention (M5 friendly g1 live finding): the reference
    # seals its mandatory caught final message at its CURRENT step (a caught thief
    # does not move); ours increments. Tolerate the repeat on that message ONLY.
    final_caught = bool(message.claim_response and message.claim_response.get("caught"))
    # M7-8: at-least-once delivery is decided BEFORE any state change, exactly like
    # validation — a redelivery must leave this session bit-identical to before it.
    verdict = session.sequencer.classify(
        step=message.step, commit=message.commit, expected=expected, final_caught=final_caught
    )
    if verdict.disposition == inbox_order.ILLEGAL:
        raise session.collapse(verdict.reason)
    if verdict.disposition == inbox_order.DUPLICATE:
        return _tolerated(message.step, inbox_order.DUPLICATE)
    if verdict.disposition == inbox_order.BUFFERED:
        session.sequencer.hold(step=message.step, commit=message.commit, raw=raw)
        return _tolerated(message.step, inbox_order.BUFFERED)
    session.sequencer.record(message.commit)
    session.inbound.append(message)
    # M7-23 (PRD_scent §10): validate the transmitted grid against the locked physics
    # BEFORE anything consumes it. Gated on the ARRIVING grid, not on the model's
    # `transmitted` flag — our sender transmits unconditionally (the reference send()
    # mirror), so under a book-v1 lock grids are on the wire and belief reads them.
    # A refused frame is withheld whole (belief + known_field) but still serves as
    # the NEXT frame's baseline, so one bad frame poisons at most two comparisons
    # and honest traffic re-accepts on its own (self-healing). Evidence-grade only.
    scent_ok = True
    if session.private.frame_check and message.smell_grid and not final_caught:
        scent_ok = frame_explained(
            session.inbound[-2].smell_grid if len(session.inbound) > 1 else {},
            message.smell_grid,
            model=session.known_field.model,
            board_size=session.constitution.board.grid_size,
            origin=session.constitution.board.axis_start_index,
            intensity=session.constitution.pheromones.center_intensity,
            tolerance=session.private.scent_physics_tolerance,
        )
        if not scent_ok:
            session.scent_refusals.append({"step": message.step, "cells": len(message.smell_grid)})
    # F9: a declared barrier is sealed/audited evidence — it constrains OUR OWN move
    # legality (the M2 gap) and the belief motion model, before anything else reads it.
    if message.barrier_placed is not None:
        barrier = (message.barrier_placed[0], message.barrier_placed[1])
        session.board = session.board.with_barrier(barrier)
        session.belief.note_barrier(barrier)
        # M7-29 (rules 46/47, App E p.149 ← ch.3): the thief adjudicates capture
        # against ITSELF at the moment the seal lands — a barrier on our own cell
        # (46) or every escape blocked (47) is a capture, and the concession is
        # automatic and sealed, with no strategy input in the path (the same
        # predicate our cop and referee already consume; the peer thief was the
        # one consumer missing — the Round-20 warm-up defect). The concede rides
        # the existing mandatory caught-final shape on our next turn.
        if (
            session.role == "thief"
            and not session.caught
            and (
                tuple(session.position) in session.board.barriers
                or is_imprisoned(session.board, session.position)
            )
        ):
            session.caught = True
            session.pending_claim_response = {"claim": list(session.position), "caught": True}
    # PRD_belief §4 pipeline (reference order): predict, then sharpen with the scent.
    session.belief.predict()
    # M7-18: a declared claim names the sender's post-move cell exactly, so it lands
    # AFTER predict (it describes where they ARE, not where they were) and BEFORE the
    # probabilistic evidence — certainty first, mirroring the barrier's treatment above.
    # Absence is deliberately not read (PRD_claims §4.2): it identifies the sender only
    # if they claim unconditionally, and misleads if they do not.
    if message.capture_claim is not None:
        session.belief.note_claim((message.capture_claim[0], message.capture_claim[1]))
    if scent_ok:
        session.belief.update_scent(message.smell_grid)
    elif session.private.refused_frame_trust > 0.0:
        # M13 quarantine (ADR-0016): a physics-refused frame stays out of the known
        # field and the audit evidence, but the belief reads it at scaled trust —
        # SQ3's multiplicative floor bounds fabrication damage, and the najamjad
        # counted proved blindness (35/35 refusals, argmax 0/34) costs more.
        session.belief.update_scent(
            message.smell_grid, trust_scale=session.private.refused_frame_trust
        )
    # M3-4: their hint feeds the belief ONLY through the closed-vocabulary parser —
    # adversarial text maps to a known landmark or to nothing (injection-safe by shape).
    if session.gazetteer is not None:
        landmark = session.gazetteer.parse(
            message.hint, max_words=session.constitution.world.hint_max_words
        )
        if landmark is not None:
            session.belief.update_hint(session.gazetteer.cells_for(landmark))
    # SQ1 receive side, M3-8 cadence policy: absorb their transmitted trail, then one
    # per-message decay — both gated on the named model's RECEIVE contract (kit SPEC §7
    # `transmitted` / `receiver_side_decay`; ADR-0004 v2). NB the M7-23 probe: that
    # contract is honored HERE only — the send path transmits unconditionally (open
    # decision M7-24), which is why the frame check above never consults the flag.
    if session.known_field.transmitted and scent_ok:
        session.known_field.absorb(message.smell_grid)
    if session.known_field.receiver_side_decay:
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
    return {"status": "ok", "step": message.step, "disposition": inbox_order.ACCEPTED}

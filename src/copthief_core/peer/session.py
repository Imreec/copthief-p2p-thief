"""PeerSession — one mini-game's protocol driver (PLAN §4; PRD FR-8 single gateway).

Owns the state machine, position, sealed records, and the four tool handlers. Every
inbound dict is adversarial until the wire layer accepts it; any protocol violation
collapses the machine to TECHNICAL_LOSS *before* the error propagates (App E rules 3–7).
M1 scope: geometric play to survival (capture-claim flow lands with SQ2 at M2/M3);
police initiates (M1 stub — the reference's first-mover convention is M2-verified).
"""

from __future__ import annotations

from typing import Any

from copthief_core.domain.crypto import make_nonce, terms_signature
from copthief_core.domain.state_machine import GameState, GameStateMachine
from copthief_core.domain.terms import terms_from_config
from copthief_core.peer.policy import SkeletonPolicy
from copthief_core.peer.sealing import SealedTurn, seal_turn
from copthief_core.shared.config_model import Constitution, PrivateSettings
from copthief_core.wire.turn import TurnMessage
from copthief_core.wire.validation import WireValidationError


class NegotiationError(RuntimeError):
    """The pre-game gate refused: terms drift or a bad signature (kit §4)."""


class ProtocolViolationError(RuntimeError):
    """An inbound message broke the protocol; the session is already in TECHNICAL_LOSS."""


class PeerSession:
    """One peer's mini-game session (Input: validated config + role; see handlers)."""

    def __init__(
        self, constitution: Constitution, private: PrivateSettings, *, role: str, seed: int
    ) -> None:
        self.constitution = constitution
        self.private = private
        self.role = role
        self.board = constitution.board.make_board()
        self.position = (
            constitution.board.cop_start if role == "police" else constitution.board.thief_start
        )
        self.machine = GameStateMachine(
            state=GameState.COMPUTING_MOVE if role == "police" else GameState.WAITING_FOR_OPPONENT
        )
        self.policy = SkeletonPolicy(seed=seed)
        self.records: list[SealedTurn] = []
        self.inbound: list[TurnMessage] = []
        self.game_uid: str | None = None
        self.opponent_group: str | None = None

    # -- handshake (PLAN §4) ---------------------------------------------------------

    def negotiate_payload(self) -> dict[str, Any]:
        """Our side of the gate: terms + fresh-nonce signature + identity."""
        terms = terms_from_config(self.constitution)
        nonce = make_nonce()
        return {
            "group_id": self.private.group_id,
            "role": self.role,
            "terms": terms,
            "nonce": nonce,
            "signature": terms_signature(terms, nonce),
        }

    def handle_negotiate(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Verify value-equal terms + the opponent's signature; lock the game_uid."""
        from copthief_core.domain.crypto import canonical_str, game_uid  # local: avoid cycle

        ours = terms_from_config(self.constitution)
        theirs = raw.get("terms")
        if canonical_str(theirs) != canonical_str(ours):
            raise NegotiationError("terms mismatch: opponent terms do not value-equal ours")
        if terms_signature(ours, str(raw.get("nonce"))) != raw.get("signature"):
            raise NegotiationError("signature verification failed over our terms")
        self.opponent_group = str(raw.get("group_id"))
        self.game_uid = game_uid(ours, self.private.group_id, self.opponent_group)
        return {"status": "ok", "game_uid": self.game_uid}

    # -- turn cycle (PLAN §5 choreography) -------------------------------------------

    def take_turn(self, *, now: float) -> dict[str, Any]:
        """Pick → seal → build the outbound TurnMessage; nonce stays withheld."""
        if self.machine.state is GameState.WAITING_FOR_OPPONENT:
            self.machine.advance(GameState.COMPUTING_MOVE)
        move = self.policy.pick_move(self.board, self.position, self.constitution.movement.move_set)
        self.position = self.board.apply_move(self.position, move)
        step = len(self.records) + 1
        hint = self.policy.next_hint(hint_max_words=self.constitution.world.hint_max_words)
        sealed = seal_turn(
            step=step,
            grid_size=self.constitution.board.grid_size,
            position=self.position,
            barriers=self.board.barriers,
            move=move,
            intent="truth",
            hint=hint,
        )
        self.records.append(sealed)
        self.machine.advance(GameState.COMMITTING)
        self.machine.advance(GameState.AWAITING_REVEAL)
        return TurnMessage(
            step=step,
            sender=self.role,
            hint=hint,
            smell_grid={},  # scent field lands at M3-2 (kit §5)
            commit=sealed.commit,
            timestamp=now,
        ).to_wire()

    def collapse(self, reason: str) -> ProtocolViolationError:
        """Record the violation as TECHNICAL_LOSS, then hand back the error to raise."""
        if not self.machine.is_terminal:
            self.machine.advance(GameState.TECHNICAL_LOSS)
        return ProtocolViolationError(reason)

    def handle_receive_turn(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Validate the inbound turn BEFORE any state change; then advance the machine."""
        try:
            message = TurnMessage.from_wire(raw)
        except WireValidationError as error:
            raise self.collapse(str(error)) from error
        expected = len(self.inbound) + 1
        if message.step != expected:
            raise self.collapse(f"step discontinuity: expected {expected}, got {message.step}")
        self.inbound.append(message)
        if self.machine.state is GameState.WAITING_FOR_OPPONENT:
            self.machine.advance(GameState.COMPUTING_MOVE)
        elif self.machine.state is GameState.AWAITING_REVEAL:
            self.machine.advance(GameState.VERIFYING)
            threshold = self.constitution.movement.survival_threshold
            if len(self.records) >= threshold and len(self.inbound) >= threshold:
                self.machine.advance(GameState.GAME_OVER)
            else:
                self.machine.advance(GameState.WAITING_FOR_OPPONENT)
        else:
            raise self.collapse(f"turn arrived in state {self.machine.state.name}")
        return {"status": "ok", "step": message.step}

    def handle_receive_control(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Opt-in status channel — answered without touching game state (never sealed)."""
        from copthief_core.wire.audit import ControlMessage

        message = ControlMessage.from_wire(raw)
        return {"status": "ok", "action": message.action, "state": self.machine.state.value}

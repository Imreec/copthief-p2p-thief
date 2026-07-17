"""PeerSession — one mini-game's protocol driver (PLAN §4; PRD FR-8 single gateway).

Owns the state machine, position, sealed records, and the tool handlers. Every inbound
dict is adversarial until the wire layer accepts it; any protocol violation collapses the
machine to TECHNICAL_LOSS *before* the error propagates (App E rules 3–7). Reference
semantics pinned at M2 (oracle sha 960499fd): the thief moves first; the police claims
its landing cell on every moving turn; the thief answers claims honestly (a caught thief
sends the final message); the thief's threshold turn carries the survival win claim.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from copthief_core.domain.state_machine import GameState, GameStateMachine
from copthief_core.peer import handshake
from copthief_core.peer.handshake import NegotiationError
from copthief_core.peer.policy import SkeletonPolicy
from copthief_core.peer.sealing import SealedTurn, seal_turn
from copthief_core.shared.config_model import Constitution, PrivateSettings
from copthief_core.wire.turn import TurnMessage
from copthief_core.wire.validation import WireValidationError

__all__ = ["FINAL_CAUGHT_HINT", "NegotiationError", "PeerSession", "ProtocolViolationError"]

# The mandatory "you got me" final message (fixed protocol text, mirrors the reference).
FINAL_CAUGHT_HINT = "You got me."


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
        # F2: the THIEF takes the first game turn; the police starts in the receive loop.
        self.machine = GameStateMachine(
            state=GameState.COMPUTING_MOVE if role == "thief" else GameState.WAITING_FOR_OPPONENT
        )
        self.policy: Any = SkeletonPolicy(seed=seed)  # duck-typed seam (BrainBase at M3-5)
        self.records: list[SealedTurn] = []
        self.inbound: list[TurnMessage] = []
        self.game_uid: str | None = None
        self.opponent_group: str | None = None
        self.outcome: str | None = None  # set by protocol events, cross-checked at audit
        self.pending_claim_response: dict[str, Any] | None = None
        self._caught = False

    # -- handshake (PLAN §4; peer/handshake) -----------------------------------------

    def negotiate_payload(self) -> dict[str, Any]:
        """Our side of the gate (delegates to peer/handshake)."""
        return handshake.negotiate_payload(self)

    def handle_negotiate(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Verify the opponent's agreement; lock the game_uid (peer/handshake)."""
        return handshake.handle_negotiate(self, raw)

    # -- turn cycle (PLAN §5 choreography) -------------------------------------------

    def take_turn(self, *, now: float) -> dict[str, Any]:
        """Pick → seal → build the outbound TurnMessage; nonce stays withheld."""
        if self.machine.state is GameState.WAITING_FOR_OPPONENT:
            self.machine.advance(GameState.COMPUTING_MOVE)
        if self._caught:  # the mandatory final message: no move, honest answer
            move, hint = "STAY", FINAL_CAUGHT_HINT
        else:
            move = self.policy.pick_move(
                self.board, self.position, self.constitution.movement.move_set
            )
            self.position = self.board.apply_move(self.position, move)
            hint = self.policy.next_hint(hint_max_words=self.constitution.world.hint_max_words)
        step = len(self.records) + 1
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
        message = TurnMessage(
            step=step,
            sender=self.role,
            hint=hint,
            smell_grid={},  # scent field lands at M3-2 (kit §5)
            commit=sealed.commit,
            # F5: ISO-8601 UTC string from the caller epoch — no clock read here.
            timestamp=datetime.fromtimestamp(now, UTC).isoformat(),
            # SQ2: the police claims its landing cell on every MOVING turn — free,
            # automatic; STAY claims nothing (mirrors MoveType.MOVE-only claims).
            capture_claim=self.position if self.role == "police" and move != "STAY" else None,
            claim_response=self.pending_claim_response,
            win_claim=self._win_claim(step),
        ).to_wire()
        self.pending_claim_response = None
        if self._caught:
            self.outcome = "cop_capture"
            self.machine.advance(GameState.VERIFYING)
            self.machine.advance(GameState.GAME_OVER)
        return message

    def _win_claim(self, step: int) -> dict[str, Any] | None:
        """The thief's survival claim on its threshold turn (never when caught) — F2."""
        threshold = self.constitution.movement.survival_threshold
        if self.role == "thief" and not self._caught and step >= threshold:
            self.outcome = "thief_survival"
            self.machine.advance(GameState.VERIFYING)
            self.machine.advance(GameState.GAME_OVER)
            return {"type": "survival"}
        return None

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
        if message.capture_claim is not None:  # SQ2: answer honestly on our next turn
            self._caught = tuple(message.capture_claim) == tuple(self.position)
            self.pending_claim_response = {
                "claim": list(message.capture_claim),
                "caught": self._caught,
            }
        if self.machine.state is GameState.WAITING_FOR_OPPONENT:
            self.machine.advance(GameState.COMPUTING_MOVE)
        elif self.machine.state is GameState.AWAITING_REVEAL:
            self.machine.advance(GameState.VERIFYING)
            if message.claim_response is not None and message.claim_response.get("caught"):
                self.outcome = "cop_capture"  # their honest answer; audit re-proves it
                self.machine.advance(GameState.GAME_OVER)
            elif message.win_claim is not None:
                self.outcome = "thief_survival"  # cross-checked at audit (threshold)
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
        return {"status": "ok", "kind": message.kind, "state": self.machine.state.value}

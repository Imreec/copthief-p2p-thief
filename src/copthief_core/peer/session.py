"""PeerSession — one mini-game's protocol driver (PLAN §4; PRD FR-8 single gateway).

Owns the state machine, position, sealed records, scent fields, and the tool handlers.
Every inbound dict is adversarial until the wire layer accepts it; any protocol
violation collapses the machine to TECHNICAL_LOSS *before* the error propagates
(App E rules 3–7). Reference semantics pinned at M2 (oracle sha 960499fd); the turn
cycle itself lives in peer/turns (the reference's turn_sender/turn_handler split),
the handshake in peer/handshake.
"""

from __future__ import annotations

from typing import Any

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.gazetteer import Gazetteer
from copthief_core.domain.scent import ScentField
from copthief_core.domain.state_machine import GameState, GameStateMachine
from copthief_core.peer import handshake, turns
from copthief_core.peer.handshake import NegotiationError
from copthief_core.peer.policy import SkeletonPolicy
from copthief_core.peer.sealing import SealedTurn
from copthief_core.peer.turns import FINAL_CAUGHT_HINT
from copthief_core.shared.config_model import Constitution, PrivateSettings
from copthief_core.strategy.brains import make_brain
from copthief_core.wire.turn import TurnMessage

__all__ = ["FINAL_CAUGHT_HINT", "NegotiationError", "PeerSession", "ProtocolViolationError"]


class ProtocolViolationError(RuntimeError):
    """An inbound message broke the protocol; the session is already in TECHNICAL_LOSS."""


def _make_scent_field(constitution: Constitution) -> ScentField:
    """One scent field under the signed pheromone params + board axis contract."""
    return ScentField(
        board_size=constitution.board.grid_size,
        window=constitution.pheromones.grid_size,
        decay=constitution.pheromones.decay,
        min_center_intensity=constitution.pheromones.min_center_intensity,
        origin=constitution.board.axis_start_index,
    )


class PeerSession:
    """One peer's mini-game session (Input: validated config + role; see handlers)."""

    def __init__(
        self,
        constitution: Constitution,
        private: PrivateSettings,
        *,
        role: str,
        seed: int,
        gazetteer: Gazetteer | None = None,
    ) -> None:
        self.constitution = constitution
        self.private = private
        self.role = role
        # M3-4 verbal layer: with a (non-empty) gazetteer our hints come from the
        # template×landmark composer and inbound hints feed the belief; without one
        # the M1 policy bank still plays (empty closed world = no geography talk).
        self.gazetteer = gazetteer if gazetteer is not None and gazetteer.landmarks() else None
        self.board = constitution.board.make_board()
        self.position = (
            constitution.board.cop_start if role == "police" else constitution.board.thief_start
        )
        # F2: the THIEF takes the first game turn; the police starts in the receive loop.
        self.machine = GameStateMachine(
            state=GameState.COMPUTING_MOVE if role == "thief" else GameState.WAITING_FOR_OPPONENT
        )
        # M3-5 BrainBase seam: moves come from the config-selected brain reading the
        # belief; the M1 policy remains ONLY as the no-gazetteer hint fallback.
        self.brain: Any = make_brain(
            private.police_class if role == "police" else private.thief_class, seed=seed
        )
        self.policy: Any = SkeletonPolicy(seed=seed)
        self.records: list[SealedTurn] = []
        self.inbound: list[TurnMessage] = []
        self.game_uid: str | None = None
        self.opponent_group: str | None = None
        self.outcome: str | None = None  # set by protocol events, cross-checked at audit
        self.pending_claim_response: dict[str, Any] | None = None
        self.caught = False
        # PRD_scent §3: two fields — own_trail's snapshot crosses the wire (never a
        # coordinate); known_field stores what the opponent transmitted (belief input).
        self.own_trail = _make_scent_field(constitution)
        self.known_field = _make_scent_field(constitution)
        # Locked scent-model hashes (PRD_scent §4), recorded by the handshake.
        self.scent_model_hash: str | None = None
        self.opponent_scent_model_hash: str | None = None
        # PRD_belief: the opponent's position filter, primed at THEIR signed start;
        # peer/turns runs its predict/update pipeline on every inbound message.
        self.belief = BeliefFilter(
            board=self.board,
            move_set=constitution.movement.move_set,
            start=(
                constitution.board.thief_start if role == "police" else constitution.board.cop_start
            ),
            center_intensity=constitution.pheromones.center_intensity,
            decay=constitution.pheromones.decay,
            smell_trust=private.smell_trust_weight,
            hint_trust=private.hint_trust_default,
        )

    # -- handshake (PLAN §4; peer/handshake) -----------------------------------------

    def negotiate_payload(self) -> dict[str, Any]:
        """Our side of the gate (delegates to peer/handshake)."""
        return handshake.negotiate_payload(self)

    def handle_negotiate(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Verify the opponent's agreement; lock the game_uid (peer/handshake)."""
        return handshake.handle_negotiate(self, raw)

    # -- turn cycle (PLAN §5 choreography; peer/turns) --------------------------------

    def take_turn(self, *, now: float) -> dict[str, Any]:
        """Pick → seal → deposit scent → outbound TurnMessage (delegates to peer/turns)."""
        return turns.take_turn(self, now=now)

    def handle_receive_turn(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Validate, absorb scent, advance the machine (delegates to peer/turns)."""
        return turns.handle_receive_turn(self, raw)

    def collapse(self, reason: str) -> ProtocolViolationError:
        """Record the violation as TECHNICAL_LOSS, then hand back the error to raise."""
        if not self.machine.is_terminal:
            self.machine.advance(GameState.TECHNICAL_LOSS)
        return ProtocolViolationError(reason)

    def handle_receive_control(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Opt-in status channel — answered without touching game state (never sealed)."""
        from copthief_core.wire.audit import ControlMessage

        message = ControlMessage.from_wire(raw)
        return {"status": "ok", "kind": message.kind, "state": self.machine.state.value}

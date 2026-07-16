"""Game state machine (book ch.8; PLAN §5): an explicit table, nothing implicit.

Every mini-game phase transition is checked against the frozen table below; anything
else raises immediately — a protocol bug surfaces in development as an exception, never
in a match as a silent freeze (App E rules 3–7). The machine holds only the state label;
deadlines and the watchdog live at the peer layer (M1-6), which drives this machine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class GameState(Enum):
    """The mini-game phases (PLAN §5). GAME_OVER / TECHNICAL_LOSS are terminal."""

    WAITING_FOR_OPPONENT = "waiting_for_opponent"
    COMPUTING_MOVE = "computing_move"
    COMMITTING = "committing"
    AWAITING_REVEAL = "awaiting_reveal"
    VERIFYING = "verifying"
    GAME_OVER = "game_over"
    TECHNICAL_LOSS = "technical_loss"


class IllegalTransitionError(RuntimeError):
    """A transition outside the PLAN §5 table was attempted — always a caller bug."""


_TERMINAL = frozenset({GameState.GAME_OVER, GameState.TECHNICAL_LOSS})
_COMM_STATES = frozenset(GameState) - _TERMINAL

# The PLAN §5 table: the turn cycle, VERIFYING's two exits, and the escape hatch —
# any communicating state may collapse to TECHNICAL_LOSS (deadline exhaustion,
# illegal inbound action, protocol violation).
_TRANSITIONS: frozenset[tuple[GameState, GameState]] = frozenset(
    {
        (GameState.WAITING_FOR_OPPONENT, GameState.COMPUTING_MOVE),
        (GameState.COMPUTING_MOVE, GameState.COMMITTING),
        (GameState.COMMITTING, GameState.AWAITING_REVEAL),
        (GameState.AWAITING_REVEAL, GameState.VERIFYING),
        (GameState.VERIFYING, GameState.WAITING_FOR_OPPONENT),
        (GameState.VERIFYING, GameState.GAME_OVER),
    }
    | {(comm, GameState.TECHNICAL_LOSS) for comm in _COMM_STATES}
)


@dataclass
class GameStateMachine:
    """One mini-game's phase tracker.

    Input: the initial state — WAITING_FOR_OPPONENT by default; the first mover starts
    at COMPUTING_MOVE (PLAN §4 handshake fixes who moves first). Output: `advance`
    returns the new state or raises `IllegalTransitionError` without mutating anything.
    """

    state: GameState = field(default=GameState.WAITING_FOR_OPPONENT)

    @property
    def is_terminal(self) -> bool:
        """True once the mini-game reached GAME_OVER (→ audit) or TECHNICAL_LOSS."""
        return self.state in _TERMINAL

    def advance(self, target: GameState) -> GameState:
        """Move to `target` iff the PLAN §5 table allows it; refuse loudly otherwise."""
        if (self.state, target) not in _TRANSITIONS:
            raise IllegalTransitionError(
                f"illegal transition {self.state.name} -> {target.name} (PLAN s5 table)"
            )
        self.state = target
        return self.state

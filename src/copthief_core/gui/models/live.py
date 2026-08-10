"""Live view-model (PRD_gui_replay §4): a pure fold over the schema-v1.1 event stream.

Local truth BY CONSTRUCTION (App E rules 8–9): the only input is the local event
stream — which carries no opponent position before the audit — the state dataclass has
no opponent field to populate, and this module imports no full-information machinery.
All three facts are pinned structurally by tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from copthief_core.domain.board import Board, Coord
from copthief_core.domain.state_machine import GameState
from copthief_core.strategy.decision import BARRIER_MOVE

# Book §7.3.2 fixed banner labels: green while the move is ours, gray once committed.
BANNER_YOUR_TURN = "YOUR TURN"
BANNER_LOCKED = "LOCKED"
_TERMINAL = frozenset({GameState.GAME_OVER, GameState.TECHNICAL_LOSS})


def heat_color(p: float, *, low: str, high: str) -> str:
    """Linear interpolation between two '#rrggbb' anchors — deeper red ⇒ higher
    probability (book fig. 9). Anchors come from `game.toml [gui]`, never from code."""
    mixed = (round(a + (b - a) * p) for a, b in zip(_channels(low), _channels(high), strict=True))
    return "#" + "".join(f"{c:02x}" for c in mixed)


def _channels(color: str) -> tuple[int, int, int]:
    """'#rrggbb' → (r, g, b)."""
    return (int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16))


@dataclass(frozen=True)
class LiveViewState:
    """One render frame of the live window — strictly local truth."""

    role: str
    step: int
    banner: str
    banner_color: str
    own_position: Coord
    barriers: frozenset[Coord]
    belief: dict[str, float]
    argmax: str
    hint_in: str
    hint_out: str
    outcome: str
    finished: bool


class LiveViewModel:
    """Fold schema-v1.1 events into render frames (Input: role + signed board geometry
    + our signed start cell; Output: `state()` snapshots for the rendering shell)."""

    def __init__(self, *, role: str, board: Board, start: Coord) -> None:
        self._role, self._board = role, board
        self._position = start
        self._step = 0
        self._banner, self._color = BANNER_LOCKED, "gray"
        self._barriers: set[Coord] = set()
        self._belief: dict[str, float] = {}
        self._argmax = ""
        self._hint_in = ""
        self._hint_out = ""
        self._outcome = ""
        self._finished = False

    def apply(self, event: dict[str, Any]) -> None:  # noqa: C901 - one branch per event kind
        """Absorb one logged event; events for the other role are ignored wholesale."""
        kind, mine = event.get("event"), event.get("sender") == self._role
        if kind == "transition" and mine:
            self._on_transition(str(event["payload"]["to"]))
        elif kind == "belief" and mine:
            self._belief = dict(event["payload"]["grid"])
            self._argmax = str(event["payload"]["argmax"])
        elif kind == "decision" and mine:
            self._step = int(event["payload"]["step"])
            move = str(event["payload"]["move"])
            # A wall turn forgoes the step (reference BARRIER semantics, M5-2):
            # the position holds; the wall itself lands via the turn event.
            if move != BARRIER_MOVE:
                self._position = self._board.apply_move(self._position, move)
        elif kind == "turn" and mine:
            self._hint_out = str(event["message"].get("hint") or "")
            self._note_barrier(event["message"].get("barrier_placed"))
        elif kind == "turn_received" and event.get("receiver") == self._role:
            self._hint_in = str(event["raw"].get("hint") or "")
            self._note_barrier(event["raw"].get("barrier_placed"))
        elif kind == "result" or (kind == "peer_result" and mine):
            self._outcome = str(event["payload"].get("outcome") or self._outcome)

    def _on_transition(self, to: str) -> None:
        state = GameState(to)
        if state in _TERMINAL:
            self._finished = True
            self._banner, self._color = state.value, "gray"
        elif state is GameState.COMPUTING_MOVE:
            self._banner, self._color = BANNER_YOUR_TURN, "green"
        else:
            self._banner, self._color = BANNER_LOCKED, "gray"

    def _note_barrier(self, value: Any) -> None:  # noqa: ANN401 - adversarial input
        """Accept only a well-formed [row, col]; pre-validation garbage is display-inert."""
        if isinstance(value, list | tuple) and len(value) == 2:
            row, col = value
            if isinstance(row, int) and isinstance(col, int):
                self._barriers.add((row, col))

    def state(self) -> LiveViewState:
        """The current render frame (frozen snapshot)."""
        return LiveViewState(
            role=self._role,
            step=self._step,
            banner=self._banner,
            banner_color=self._color,
            own_position=self._position,
            barriers=frozenset(self._barriers),
            belief=dict(self._belief),
            argmax=self._argmax,
            hint_in=self._hint_in,
            hint_out=self._hint_out,
            outcome=self._outcome,
            finished=self._finished,
        )

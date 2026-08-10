"""vibecode's thief as an arena arm (M10 rebuild) — modeled from OUR OWN logs.

Rebuilt 2026-08-10 from the audit-revealed positions of the uncounted friendly we
lost 30–90 (`logs/imreeyal-vs-vibecode_g01/g03/g05.jsonl`, 105 sealed thief steps).
The pre-08-10 model — a south-edge corner oscillator read off anrbj666's archived
2026-08 series — is DEAD: the fielded thief never visits a corner and never leaves
the center. Observed policy, identical in shape across all three games:

- a short opening wander out of the (3,3) spawn (S/N dithering, one STAY);
- then a fixed six-cell COUNTERCLOCKWISE loop around board center, held for 25+
  consecutive steps in every game: (3,3)→S→(4,3)→E→(4,4)→N→(3,4)→N→(2,4)→W→
  (2,3)→S→(3,3);
- a vertical sprint away from our cop in the final 3-4 steps (N,N,N,N in g03/g05
  with the cop south; S,S,S,E in g01 with the cop north);
- never a barrier; exactly ONE STAY per game, each under a diagonal cut ((4,4)@7
  in g03/g05, (2,2)@11 in g01) — modeled as the hold that answers a cop covering
  both ring arcs at once.

Fidelity is a BEHAVIORAL APPROXIMATION, not a port: the opening wander is
flattened into a greedy walk onto the loop, and the single sprint knob is the one
free parameter (`VIBECODE_THIEF_DEFAULTS`, arena-overridable). Loop cells are
board geometry — center plus fixed offsets — so the model scales with the signed
board. One ingredient is INFERRED, not observed: against our follower cop the
loop direction never had to change, but a scripted ring with no cop awareness is
caught in ~5 steps by an intercepting cop, which the real thief demonstrably was
not (105 steps, 0 captures) — so the model reverses direction when the next ring
cell sits in the believed cop's step-on reach (the minimal mechanism that makes a
ring runner uncatchable without walls, matching both the logs and pursuit theory).
Off the observed data (broken ring, both arcs threatened) the model extrapolates.
"""

from __future__ import annotations

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import Board, Coord
from copthief_core.strategy.brains import BrainBase, Observation

__all__ = ["VIBECODE_THIEF_DEFAULTS", "VibecodeThiefBrain"]

VIBECODE_THIEF_DEFAULTS: dict[str, float] = {
    "sprint_steps": 3.0,  # final steps that break the loop into the vertical sprint
}

# The observed loop as offsets from board center, in play order (S,E,N,N,W,S).
_LOOP_OFFSETS: tuple[Coord, ...] = ((0, 0), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0))

_STEP_TO_MOVE: dict[Coord, str] = {(1, 0): "S", (-1, 0): "N", (0, 1): "E", (0, -1): "W"}


def _loop_cells(board: Board) -> tuple[Coord, ...]:
    """The six loop cells for this board: center + the logged offsets."""
    mid = board.axis_start_index + board.grid_size // 2
    return tuple((mid + dr, mid + dc) for dr, dc in _LOOP_OFFSETS)


def _toward(position: Coord, target: Coord) -> str:
    """One greedy step toward `target` (rows first — the observed S-leaning walk)."""
    if target[0] != position[0]:
        return "S" if target[0] > position[0] else "N"
    return "E" if target[1] > position[1] else "W"


def _dodge(board: Board, position: Coord, cop: Coord) -> str:
    """The extrapolated evasion step: the move maximizing believed-cop distance."""
    dodges = [(move, board.apply_move(position, move)) for move in ("E", "N", "S", "W")]
    return max(dodges, key=lambda md: (abs(md[1][0] - cop[0]) + abs(md[1][1] - cop[1]), md[0]))[0]


class VibecodeThiefBrain(BrainBase):
    """Central hex-loop oscillator + endgame sprint (their audit-revealed thief).

    Input:  the observation and our belief over the cop's cell.
    Output: the scripted move for the current phase — the loop's next edge when on
            a loop cell, a greedy step onto the loop otherwise, and the vertical
            sprint away from the believed cop once the clock nears the threshold.
            Never STAY, never a barrier; the template clamps a blocked move.
    """

    _direction: int = 1  # +1 = the observed counterclockwise lap; reversals persist

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        opts = {**VIBECODE_THIEF_DEFAULTS, **self._options}
        board, position = observation.board, observation.position
        cop = belief.argmax()
        threshold = observation.survival_threshold
        if threshold > 0 and observation.step > threshold - opts["sprint_steps"]:
            # The observed break: run the column away from the believed cop.
            return "N" if cop[0] > position[0] else "S"
        loop = _loop_cells(board)
        if position in loop:
            index = loop.index(position)
            for direction in (self._direction, -self._direction):
                nxt = loop[(index + direction) % len(loop)]
                threatened = abs(nxt[0] - cop[0]) + abs(nxt[1] - cop[1]) <= 1
                if not board.is_blocked(nxt) and not threatened:
                    self._direction = direction
                    return _toward(position, nxt)
            # Both arcs threatened: the logged answer to a diagonal cut is the one
            # STAY each game shows ((4,4)@7 in g03/g05, (2,2)@11 in g01) — hold
            # until the cop commits to a side, then run the other arc. Only when
            # our own cell is itself in reach does the model dodge off-ring.
            if abs(position[0] - cop[0]) + abs(position[1] - cop[1]) > 1:
                return "STAY"
            return _dodge(board, position, cop)
        open_loop = [cell for cell in loop if not board.is_blocked(cell)] or list(loop)
        target = max(
            open_loop, key=lambda cell: (abs(cell[0] - cop[0]) + abs(cell[1] - cop[1]), cell)
        )
        approach = _toward(position, target)
        landing = board.apply_move(position, approach)
        if abs(landing[0] - cop[0]) + abs(landing[1] - cop[1]) <= 1:
            return _dodge(board, position, cop)  # re-enter without crossing the cop
        return approach

"""vibecode's cop as an arena arm (M10 rebuild) — modeled from OUR OWN logs.

Rebuilt 2026-08-10 from the sealed cop records of the uncounted friendly we lost
30–90 (`logs/imreeyal-vs-vibecode_g02/g04/g06.jsonl`, 43 cop steps, 3 captures at
steps 13–15). The pre-08-10 model — east-wall habit, wall-blind Manhattan dithering,
wasted re-placements, read off anrbj666's archived series — is DEAD. Observed now:

- a scripted S,S,S opening out of the (0,0) spawn (all three games);
- a wall-aware chase that tracked our honest scent to Chebyshev 1 by ~step 10
  (no dithering, no wasted turns) — modeled as BFS-greedy on the belief argmax;
- exactly ONE barrier per game, and always the same shape: the believed thief
  penned on a ≤2-escape cell, the reachable escape walled ((0,5) under the (0,6)
  corner in g04/g06; (6,5) under (6,6) in g02), capture 1-2 turns later;
- a capture claim on its own sealed cell EVERY turn (43/43 truthful) — claims are
  loop-level physics, so the arena models that with `claim_threshold: 0.0` on this
  arm's roster entry, not here (PRD_claims §5).

Fidelity is a BEHAVIORAL APPROXIMATION, not a port: the seal tie-break is
deterministic (sorted among equal-region walls — g02's (6,5) vs our (5,6) is a
divergence between symmetric seals), and their unseen belief is replaced by ours.
"""

from __future__ import annotations

import math

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import STAY, Coord
from copthief_core.domain.rules import legal_moves
from copthief_core.strategy.brains import BrainBase, Observation
from copthief_core.strategy.decision import Decision, barrier_is_playable
from copthief_core.strategy.region import path_length, region_size

__all__ = ["VIBECODE_COP_DEFAULTS", "VibecodeCopBrain"]

VIBECODE_COP_DEFAULTS: dict[str, float] = {
    "opening_steps": 3.0,  # scripted S,S,S out of the spawn (steps 1-3, all games)
    "seal_range": 2.0,  # BFS gap within which the seal wall is considered
    "seal_escapes": 2.0,  # believed cell must be this penned before walling
    "max_walls": 1.0,  # observed: exactly one barrier per game
    # M11 (nis-yar1 arm, shares this class): hold the diagonal against a penned
    # prey instead of closing — their g02/g04/g06 cop STAYED at Chebyshev 1 for
    # three turns until zugzwang, then sealed. 0.0 = the vibecode arm unchanged.
    "pin_enabled": 0.0,
}


class VibecodeCopBrain(BrainBase):
    """Scripted opening + BFS chase + one corner-sealing wall (their fielded cop).

    Input:  the observation and our belief over the thief's cell.
    Output: a `Decision` — S during the opening; the single seal wall when the
            believed thief is penned in reach; otherwise the BFS-greedy chase step.
    Setup:  `VIBECODE_COP_DEFAULTS`, overridable through the arena's `brain_options`.
    """

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        board, prey = observation.board, belief.argmax()
        candidates = sorted(legal_moves(board, observation.position, observation.move_set))
        if not candidates:
            return STAY

        def gap_after(move: str) -> float:
            dest = board.apply_move(observation.position, move)
            gap = path_length(board, dest, prey, observation.move_set)
            return math.inf if gap is None else float(gap)

        return min(candidates, key=lambda m: (gap_after(m), m))

    def _seal_wall(
        self, observation: Observation, prey: Coord, opts: dict[str, float]
    ) -> Coord | None:
        """The one observed placement: wall a penned believed cell's reachable escape."""
        board = observation.board
        if observation.barriers_used >= opts["max_walls"]:
            return None
        gap = path_length(board, observation.position, prey, observation.move_set)
        if gap is None or gap > opts["seal_range"]:
            return None
        escapes = [cell for cell in board.neighbors(prey) if not board.is_blocked(cell)]
        if len(escapes) > opts["seal_escapes"]:
            return None
        cap = board.grid_size * board.grid_size
        walls = [
            cell
            for cell in escapes
            if barrier_is_playable(
                board,
                observation.position,
                observation.role,
                cell,
                used=observation.barriers_used,
                quota=observation.max_barriers,
            )
        ]
        if not walls:
            return None
        return min(
            walls,
            key=lambda cell: (
                region_size(board.with_barrier(cell), prey, observation.move_set, cap, {}),
                cell,
            ),
        )

    def _decide(self, observation: Observation, belief: BeliefFilter) -> Decision:
        opts = {**VIBECODE_COP_DEFAULTS, **self._options}
        if observation.step <= opts["opening_steps"]:
            return Decision(move="S")
        prey = belief.argmax()
        wall = self._seal_wall(observation, prey, opts)
        if wall is not None:
            return Decision(move=STAY, barrier=wall)
        if opts["pin_enabled"] > 0.0:
            board = observation.board
            gap = path_length(board, observation.position, prey, observation.move_set)
            escapes = sum(1 for cell in board.neighbors(prey) if not board.is_blocked(cell))
            if gap == 2 and escapes <= opts["seal_escapes"]:
                return Decision(move=STAY)  # the observed zugzwang hold
        return Decision(move=self._pick_move(observation, belief))

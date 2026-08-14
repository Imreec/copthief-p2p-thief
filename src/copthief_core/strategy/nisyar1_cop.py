"""nis-yar1's cop as an arena arm (M11 part 2) — modeled from the COUNTED logs.

The M11 arm rode VibecodeCopBrain with a pin knob and `max_walls 2`; the counted
(their `41b9fb76`, 2026-08-11 T=22:37) showed a richer, heavier shape across
g02/g04/g06 (byte-identical games — both stacks deterministic on this pairing's
fixed starts): 27/33 moves closed on our LAG-1 cell, and exactly SIX walls per
game (steps 9/18/21/27/30/34), every one adjacent to our current/lag-1 cell and
inside their own reach — trail-head escape-cutting, not the two-wall corner seal
the friendly showed. anrbj666's independent mimic of the same cop (their kill
tapes vs it) matches: approach to gap 2, hold (never close to 1), first wall at
step 9, fewest-exit seals after.

The wall rule is EXACT, not approximate: all six counted walls were placed in
DIAGONAL contact, on the sorted-first of the two cells adjacent to both cop and
prey ((4,5)/(3,2)/(4,1)/(2,0)/(1,1)/(1,4) — each verified lexicographically
first among the shared pair). The (exits, cell) tie-break below reproduces all
six. Their belief is replaced by the arena feed (`truth-lag1` — the lag their
pin measured at). Wall cadence emerges from contact, not a spacing knob: the
counted spacing (>=3) is the runner breaking contact after each cut.
"""

from __future__ import annotations

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import STAY, Coord
from copthief_core.domain.rules import legal_moves
from copthief_core.strategy.brains import BrainBase, Observation
from copthief_core.strategy.decision import Decision, barrier_is_playable
from copthief_core.strategy.region import path_length

__all__ = ["NISYAR1_COP_DEFAULTS", "NisYar1CopBrain"]

NISYAR1_COP_DEFAULTS: dict[str, float] = {
    "hold_gap": 2.0,  # the metronome: at this BFS gap the cop holds, never closes to 1
    "wall_start_step": 9.0,  # first wall observed at step 9 (both sources agree)
    "wall_range": 2.0,  # escape-cuts happen in contact (believed cell this close)
    "max_walls": 6.0,  # exactly six per counted game
}


class NisYar1CopBrain(BrainBase):
    """Lag-1 chase + metronome hold + trail-head escape-cutting (their counted cop).

    Input:  the observation and the belief over the thief (feed `truth-lag1`).
    Output: a `Decision` — from `wall_start_step`, in contact, wall the believed
            cell's reachable escape with the fewest exits; at `hold_gap` hold;
            otherwise the BFS-greedy closing step.
    Setup:  `NISYAR1_COP_DEFAULTS`, overridable through arena `brain_options`.
    """

    def _gap(self, observation: Observation, prey: Coord) -> float:
        length = path_length(observation.board, observation.position, prey, observation.move_set)
        return float("inf") if length is None else float(length)

    def _escape_cut(
        self, observation: Observation, prey: Coord, opts: dict[str, float]
    ) -> Coord | None:
        """The observed placement: cut the believed cell's fewest-exit escape."""
        board = observation.board
        if (
            observation.step < opts["wall_start_step"]
            or observation.barriers_used >= opts["max_walls"]
        ):
            return None
        if self._gap(observation, prey) > opts["wall_range"]:
            return None
        cuts = [
            cell
            for cell in board.neighbors(prey)
            if not board.is_blocked(cell)
            and cell != observation.position
            and barrier_is_playable(
                board,
                observation.position,
                observation.role,
                cell,
                used=observation.barriers_used,
                quota=observation.max_barriers,
            )
        ]
        if not cuts:
            return None

        def exits(cell: Coord) -> int:
            return sum(1 for n in board.neighbors(cell) if not board.is_blocked(n))

        return min(cuts, key=lambda cell: (exits(cell), cell))

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        board, prey = observation.board, belief.argmax()
        candidates = sorted(legal_moves(board, observation.position, observation.move_set))
        if not candidates:
            return STAY

        def gap_after(move: str) -> float:
            dest = board.apply_move(observation.position, move)
            length = path_length(board, dest, prey, observation.move_set)
            return float("inf") if length is None else float(length)

        return min(candidates, key=lambda m: (gap_after(m), m))

    def _decide(self, observation: Observation, belief: BeliefFilter) -> Decision:
        opts = {**NISYAR1_COP_DEFAULTS, **self._options}
        prey = belief.argmax()
        wall = self._escape_cut(observation, prey, opts)
        if wall is not None:
            return Decision(move=STAY, barrier=wall)
        if self._gap(observation, prey) <= opts["hold_gap"]:
            return Decision(move=STAY)  # the metronome hold — never closes to 1
        return Decision(move=self._pick_move(observation, belief))

"""nis-yar1's thief as an arena arm (M11 part 2) — refreshed from the COUNTED logs.

The M11 arm modeled their a0ba98d1 friendly (flee-then-perch: 21 consecutive
STAYs at (0,4)). The counted (2026-08-11 T=22:37) ran their `41b9fb76`, and the
perch is DEAD across all three thief games (audit-revealed positions,
`reports/counted-series/imreeyal/` + the runtime JSONLs): stays 20-25%, longest
run 4, away-moves dominate (18/28, 12/20), edge occupancy 40-54%. Observed shape:

- an opening walk away from the cop's approach line into the SE quadrant;
- sustained flight while our cop pressed (they moved even at gap 4-5);
- short rests (1-4 STAYs) only when the gap was wide, then motion resumed —
  the runner circulates near the border rather than committing to a corner.

Fidelity is a BEHAVIORAL APPROXIMATION from three counted games against one
(our) cop: flight and the dwell cap are faithfully observed; the border bias is
mirrored as a tie-break (their exact objective is unobservable). Deterministic
given (seed, options): ties break on sorted move order.
"""

from __future__ import annotations

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import STAY, Coord
from copthief_core.domain.rules import legal_moves
from copthief_core.strategy.brains import BrainBase, Observation

__all__ = ["NISYAR1_THIEF_DEFAULTS", "NisYar1ThiefBrain"]

NISYAR1_THIEF_DEFAULTS: dict[str, float] = {
    # They moved whenever our cop pressed; rests only appeared at wide gaps.
    "press_distance": 4.0,  # flee while the believed cop is this close (Manhattan)
    "dwell_cap": 3.0,  # consecutive STAYs allowed when safe (longest run: 4 incl. wake)
    "border_bias": 1.0,  # tie-break toward border-adjacent cells (edge_frac ~50%)
}


class NisYar1ThiefBrain(BrainBase):
    """Runner (their counted shape): flee under press, rest briefly, keep moving.

    Input:  the observation and our belief over the cop.
    Output: STAY only when the believed cop is beyond `press_distance` AND the
            current rest run is under `dwell_cap`; otherwise the legal move
            maximizing Manhattan distance, border-adjacent cells preferred on
            ties, then sorted move order (deterministic like every modeled arm).
    """

    _rest_run: int = 0

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        board, position = observation.board, observation.position
        cop = belief.argmax()
        candidates = sorted(legal_moves(board, position, observation.move_set))
        if not candidates:
            return STAY
        opts = {**NISYAR1_THIEF_DEFAULTS, **self._options}
        gap = abs(position[0] - cop[0]) + abs(position[1] - cop[1])
        if (
            gap > opts["press_distance"]
            and self._rest_run < opts["dwell_cap"]
            and STAY in candidates
        ):
            self._rest_run += 1
            return STAY

        def rank(move: str) -> tuple[int, float, int]:
            dest: Coord = board.apply_move(position, move)
            distance = abs(dest[0] - cop[0]) + abs(dest[1] - cop[1])
            low = board.axis_start_index
            high = low + board.grid_size - 1
            edge_gap = min(dest[0] - low, high - dest[0], dest[1] - low, high - dest[1])
            return (distance, -opts["border_bias"] * edge_gap, move != STAY)

        best = max(candidates, key=lambda m: (rank(m), m))
        self._rest_run = 0 if best != STAY else self._rest_run + 1
        return best

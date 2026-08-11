"""nis-yar1's thief as an arena arm (M11) — modeled from OUR OWN logs.

Rebuilt 2026-08-11 from the audit-revealed positions of the friendly we lost
60-80 (`docs/evidence/friendly-nis-yar1-2026-08-11/imreeyal-vs-nis-yar1_g01.jsonl`,
their commit a0ba98d1, 35 revealed thief steps — ONE game of evidence; g03/g05
were converted by our cop at 11/13 before their shape could show). Observed:

- an opening walk away from our cop's approach line ((3,3)→SE to the (6,5)
  area, then N along column 5 to (0,4));
- then a PERCH: twenty-one consecutive STAYs at (0,4) with our cop two cells
  away — where our M10 cop froze (the g01 stall, fixed by M11-C1) and conceded
  a 34-step survival.

Fidelity is a BEHAVIORAL APPROXIMATION from a single game against a frozen
cop: the perch is faithfully observed, but the wake response (what they do when
a working cop closes in) is INFERRED as resumed max-distance flight — the
minimal mechanism consistent with the opening walk. The arm's job in the pool
is exactly the g01 regression: a cop that cannot convert a perched thief
concedes 10 points to this shape.
"""

from __future__ import annotations

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import STAY, Coord
from copthief_core.domain.rules import legal_moves
from copthief_core.strategy.brains import BrainBase, Observation

__all__ = ["NISYAR1_THIEF_DEFAULTS", "NisYar1ThiefBrain"]

NISYAR1_THIEF_DEFAULTS: dict[str, float] = {
    # The perch held at Manhattan 2 in the log (21 STAYs with our cop at (2,4)),
    # so only adjacency provably wakes them: perch while gap > wake_distance.
    "wake_distance": 1.0,
}


class NisYar1ThiefBrain(BrainBase):
    """Flee-then-perch (their g01 shape): run from the believed cop, then camp.

    Input:  the observation and our belief over the cop's cell.
    Output: STAY while the believed cop is farther than `wake_distance`;
            otherwise the legal move maximizing Manhattan distance (ties break
            on sorted move order — deterministic like every modeled arm).
    """

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        board, position = observation.board, observation.position
        cop = belief.argmax()
        candidates = sorted(legal_moves(board, position, observation.move_set))
        if not candidates:
            return STAY
        opts = {**NISYAR1_THIEF_DEFAULTS, **self._options}
        gap = abs(position[0] - cop[0]) + abs(position[1] - cop[1])
        if gap > opts["wake_distance"] and STAY in candidates:
            return STAY

        def distance_after(move: str) -> tuple[int, str]:
            dest: Coord = board.apply_move(position, move)
            return (abs(dest[0] - cop[0]) + abs(dest[1] - cop[1]), move)

        return max(candidates, key=distance_after)

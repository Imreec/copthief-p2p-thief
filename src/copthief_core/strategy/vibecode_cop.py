"""vibecode's cop as an arena arm (M9 study) — modeled from audit-revealed play.

Their repos are PRIVATE, so this is reconstructed from the `opponent_records` of
anrbj666's archived counted series against them (anrbj666's thief survived g04/g06):

    P2P-Thief/results/log_anrbj666-vs-vibecode_g02.json  (34 steps)
    P2P-Thief/results/log_anrbj666-vs-vibecode_g04.json  (34 steps)
    P2P-Thief/results/log_anrbj666-vs-vibecode_g06.json  (34 steps)

Observed behavior: an S,S opening out of the (0,0) spawn in all three games; an
early PLACE_E walling (2,1) at step 3 in g02/g04 (g06 kept marching — an
input-dependence the model flattens into the deterministic habit); then an eastward
sweep through rows 1-3 placing barriers almost always EAST of itself (16 of 18
placements), clustering in the (1..3, 4..6) block; repeated WASTED placement
attempts on already-walled cells that forfeit the turn (g02 steps 31-32, g04 steps
4-5/22-23/33); 2-cell dithering loops mid-board; and NEVER a capture claim (claims
are policy-layer above the brain seam, and this arm simply has no claim surface).

Modeled as: the scripted opening, a periodic PLACE_E habit (a blocked east cell
burns the turn exactly as their wasted attempts did), and otherwise a wall-blind
greedy Manhattan chase of the belief argmax — wall-blindness is what reproduces
their dithering against their own barriers, so it is kept deliberately. Fidelity is
a BEHAVIORAL APPROXIMATION of the observed weaknesses, not a port; the belief the
arena feeds this arm is ours, likely sharper than whatever theirs was.
"""

from __future__ import annotations

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import STAY
from copthief_core.domain.rules import legal_moves
from copthief_core.strategy.brains import BrainBase, Observation
from copthief_core.strategy.decision import Decision, barrier_is_playable

__all__ = ["VIBECODE_COP_DEFAULTS", "VibecodeCopBrain"]

VIBECODE_COP_DEFAULTS: dict[str, float] = {
    "opening_steps": 2.0,  # scripted S,S out of the spawn (steps 1-2, all three games)
    "early_wall_step": 3.0,  # the (2,1) PLACE_E that opens g02/g04
    "wall_period": 4.0,  # the east-wall habit's cadence during the sweep (~1 in 4)
}


class VibecodeCopBrain(BrainBase):
    """Scripted opening + east-wall habit + wall-blind chase (their observed cop).

    Input:  the observation and our belief over the thief's cell.
    Output: a `Decision` — S during the opening; on habit steps a barrier EAST of
            itself (a burned turn when that cell is already walled, their observed
            waste); otherwise the greedy Manhattan step toward the belief argmax.
    Setup:  `VIBECODE_COP_DEFAULTS`, overridable through the arena's `brain_options`.
    """

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        target = belief.argmax()
        candidates = sorted(
            legal_moves(observation.board, observation.position, observation.move_set)
        )
        if not candidates:
            return STAY
        # Manhattan on purpose, not BFS: the observed cop bounced off its own walls
        # in 2-cell loops, which is exactly what a path-blind chase produces.
        moving = [m for m in candidates if m != STAY] or candidates

        def distance_after(move: str) -> int:
            dest = observation.board.apply_move(observation.position, move)
            return abs(dest[0] - target[0]) + abs(dest[1] - target[1])

        return min(moving, key=lambda m: (distance_after(m), m))

    def _decide(self, observation: Observation, belief: BeliefFilter) -> Decision:
        opts = {**VIBECODE_COP_DEFAULTS, **self._options}
        if observation.step <= opts["opening_steps"]:
            return Decision(move="S")
        if self._wall_urge(observation.step, opts):
            east = observation.board.apply_move(observation.position, "E")
            if barrier_is_playable(
                observation.board,
                observation.position,
                observation.role,
                east,
                used=observation.barriers_used,
                quota=observation.max_barriers,
            ):
                return Decision(move=STAY, barrier=east)
            if east in observation.board.barriers:
                # The observed waste: re-attempting an already-walled cell forfeits
                # the turn (g02 steps 31-32) instead of degrading to a move.
                return Decision(move=STAY)
        return Decision(move=self._pick_move(observation, belief))

    @staticmethod
    def _wall_urge(step: int, opts: dict[str, float]) -> bool:
        """True on the early-wall step and every `wall_period` steps after it."""
        if step < opts["early_wall_step"]:
            return False
        return (step - opts["early_wall_step"]) % opts["wall_period"] == 0

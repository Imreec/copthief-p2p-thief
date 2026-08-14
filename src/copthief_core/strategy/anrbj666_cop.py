"""anrbj666's FIELDED cop as an arena arm (M11 part 2) — their HEAD `41e907d`.

Re-implemented from behavior in the repos anrbj666 shared for study (ADR-0011
consent basis — their explicit offer after our counted pairing was played and
cannot recur; no code copied). This models the brain they FIELD (hunter-cop
models their arena instrument, a different animal): BFS chase on the believed
cell; steady-heading INTERCEPTION (project the runner, meet it — never follow);
trap walls gated on range/sharpness/cornered-ness with three studied wrinkles —
the step-in capture is preferred to the wall mid-game, the last two turns wall
the peak itself (rule 46), and four consecutive sharp contact turns RELEASE the
cornered-ness gate (their contact-dwell quota release, the counter their newest
decoy exists to bait).

Fidelity caveats: their endgame solver and info-gain term are NOT modeled (the
sharp arena feed + wall-on-peak carry conversion; info-gain is tie-shaping);
their belief pins (dwell-plateau, trail-head law-solve) are approximated by the
`sharp199` feed. Movement mirrors their tie rule: STAY is the incumbent and only
a strictly better move displaces it, in seeded-shuffle order. Their wall pick is
first-in-N/S/E/W-order; ours scans escapes in that order too.
"""

from __future__ import annotations

import math

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import STAY, Coord
from copthief_core.domain.rules import legal_moves
from copthief_core.strategy.anrbj666_intercept import intercept_target
from copthief_core.strategy.brains import BrainBase, Observation
from copthief_core.strategy.decision import Decision, barrier_is_playable
from copthief_core.strategy.region import path_length

__all__ = ["ANRBJ666_COP_DEFAULTS", "Anrbj666CopBrain", "intercept_target"]

ANRBJ666_COP_DEFAULTS: dict[str, float] = {
    "trap_range": 3.0,  # their [strategy.trap] range
    "escape_limit": 3.0,  # their [strategy.trap] escape_limit
    "dwell_release": 4.0,  # sharp contact turns that open the cornered-ness gate
    "sharp_mass": 0.45,  # their wall_mass_threshold / interception sharpness gate
    "contact_gap": 2.0,  # BFS gap that counts as contact for the dwell counter
    "horizon": 10.0,  # interception projection length
}


class Anrbj666CopBrain(BrainBase):
    """Trap wall > interception > BFS chase (their fielded pipeline, sans solver).

    Input:  the observation and the belief over the thief (feed `sharp199`).
    Output: a `Decision`. Deterministic given (seed, options).
    """

    _prev_peak: Coord | None = None
    _prev_vel: Coord | None = None
    _dwell: int = 0

    def _remaining(self, observation: Observation) -> float:
        if observation.survival_threshold <= 0:
            return math.inf
        return float(observation.survival_threshold - observation.step)

    def _trap_wall(
        self, observation: Observation, peak: Coord, sharp: bool, opts: dict[str, float]
    ) -> Coord | None:
        board, me = observation.board, observation.position
        released = self._dwell >= opts["dwell_release"]
        gap = path_length(board, me, peak, observation.move_set)
        if gap is None or gap > opts["trap_range"] or not sharp:
            return None
        escapes = [c for c in board.neighbors(peak) if not board.is_blocked(c)]
        if not released and len(escapes) > opts["escape_limit"]:
            return None
        remaining = self._remaining(observation)

        def playable(cell: Coord) -> bool:
            return barrier_is_playable(
                board,
                me,
                observation.role,
                cell,
                used=observation.barriers_used,
                quota=observation.max_barriers,
            )

        reach = {me, *board.neighbors(me)}
        if peak in reach and playable(peak):
            step_in = not released and peak != me and remaining > 2
            return None if step_in else peak  # rule-46 wall on the believed cell
        for cell in escapes:  # their N,S,E,W construction order
            if cell in reach and playable(cell):
                walled = path_length(board.with_barrier(cell), me, peak, observation.move_set)
                if walled is not None and walled <= remaining:  # never-wall-out
                    return cell
        return None

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        opts = {**ANRBJ666_COP_DEFAULTS, **self._options}
        board, me = observation.board, observation.position
        peak = belief.argmax()
        target = peak
        sharp = belief.probs().get(peak, 0.0) >= opts["sharp_mass"]
        vel: Coord | None = None
        if self._prev_peak is not None:
            delta = (peak[0] - self._prev_peak[0], peak[1] - self._prev_peak[1])
            vel = delta if abs(delta[0]) + abs(delta[1]) == 1 else None
        if vel is not None and vel == self._prev_vel and sharp:
            cut = intercept_target(
                board, me, peak, vel, observation.move_set, horizon=int(opts["horizon"])
            )
            if cut is not None:
                target = cut
        self._prev_peak, self._prev_vel = peak, vel
        candidates = [m for m in legal_moves(board, me, observation.move_set) if m != STAY]
        self._rng.shuffle(candidates)
        best, best_gap = STAY, path_length(board, me, target, observation.move_set)
        for move in candidates:
            gap = path_length(board, board.apply_move(me, move), target, observation.move_set)
            if gap is not None and (best_gap is None or gap < best_gap):
                best, best_gap = move, gap
        return best

    def _decide(self, observation: Observation, belief: BeliefFilter) -> Decision:
        opts = {**ANRBJ666_COP_DEFAULTS, **self._options}
        peak = belief.argmax()
        sharp = belief.probs().get(peak, 0.0) >= opts["sharp_mass"]
        gap = path_length(observation.board, observation.position, peak, observation.move_set)
        if gap is not None and gap <= opts["contact_gap"] and sharp:
            self._dwell += 1
        elif gap is not None and gap > opts["contact_gap"]:
            self._dwell = 0
        wall = self._trap_wall(observation, peak, sharp, opts)
        if wall is not None:
            return Decision(move=STAY, barrier=wall)  # their stale-velocity quirk mirrored
        return Decision(move=self._pick_move(observation, belief))

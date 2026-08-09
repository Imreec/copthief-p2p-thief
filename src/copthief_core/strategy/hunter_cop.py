"""Hunting-cop stress arm (M9 study) — anrbj666's arena instrument, our idiom.

Re-implemented from their PUBLISHED sparring cop `AgedBeliefTrapCop`
(P2P-Police `src/p2p_police/strategy/arena_aged_cop.py`): the hunting pattern OUR
thief must survive. It TRUSTS the belief early — pouncing once the peak's mass
clears a low threshold instead of waiting for certainty, so a camper's beacon is
punished before it can relocate — closes on the peak BFS-greedily (never
Manhattan-blind: it routes around walls), and spends wall quota only surgically:
inside `trap_range` BFS steps it walls the reachable cell that most shrinks the
believed room when the gain clears `gain_min`, and walls the peak cell ITSELF when
the belief is sharp (`kill_mass` — a wall on the thief's cell captures, rule 46).

A re-implementation against our seam via the belief read surface and the shared
region/path helpers, not a port: their movement tie-break is seeded-random and is
mirrored; their wall tie-break follows construction order and is made deterministic
(sorted) here, a divergence only among equal-gain walls.
"""

from __future__ import annotations

import math

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import STAY, Coord
from copthief_core.domain.rules import legal_moves
from copthief_core.strategy.brains import BrainBase, Observation
from copthief_core.strategy.decision import Decision, barrier_is_playable
from copthief_core.strategy.region import path_length, region_size

__all__ = ["HUNTER_DEFAULTS", "HunterCopBrain"]

HUNTER_DEFAULTS: dict[str, float] = {
    "pounce_mass": 0.08,  # their POUNCE_MASS — act even on a weak peak
    "trap_range": 3.0,  # their TRAP_RANGE — consider a wall inside this BFS gap
    "gain_min": 3.0,  # their GAIN_MIN — a wall must shrink the believed room by this
    "kill_mass": 0.30,  # their KILL_MASS — wall the peak cell only when belief is sharp
    "region_cap": 49.0,  # their bfs_distances is uncapped on a 7x7
}


class HunterCopBrain(BrainBase):
    """Belief-led pounce + surgical walls (their `AgedBeliefTrapCop` policy).

    Input:  the observation and our belief over the thief's cell.
    Output: a `Decision` — a surgical (or rule-46 kill) wall when the pounce gates
            pass, else the BFS-greedy step toward the belief peak.
    Setup:  `HUNTER_DEFAULTS`, overridable through the arena's `brain_options`.
    """

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        board = observation.board
        prey = belief.argmax()
        candidates = list(legal_moves(board, observation.position, observation.move_set))
        if not candidates:
            return STAY
        # Their tie-break is seeded-random: rng.sample then min keeps a uniform
        # draw among BFS-equal steps, so an evader cannot read the approach line.
        self._rng.shuffle(candidates)

        def gap_after(move: str) -> float:
            dest = board.apply_move(observation.position, move)
            gap = path_length(board, dest, prey, observation.move_set)
            return math.inf if gap is None else float(gap)

        return min(candidates, key=gap_after)

    def _decide(self, observation: Observation, belief: BeliefFilter) -> Decision:
        opts = {**HUNTER_DEFAULTS, **self._options}
        prey = belief.argmax()
        gap = path_length(observation.board, observation.position, prey, observation.move_set)
        if (
            belief.prob_at(prey) >= opts["pounce_mass"]
            and gap is not None
            and gap <= opts["trap_range"]
        ):
            wall = self._surgical_wall(observation, prey, belief.prob_at(prey), opts)
            if wall is not None:
                return Decision(move=STAY, barrier=wall)
        return Decision(move=self._pick_move(observation, belief))

    def _surgical_wall(
        self, observation: Observation, prey: Coord, mass: float, opts: dict[str, float]
    ) -> Coord | None:
        """Their placement rule (Output: the cell to wall, or None to keep moving).

        A sharp peak inside placement reach is walled directly (rule-46 capture);
        otherwise the reachable wall that most shrinks the believed room is placed
        when its gain clears `gain_min`.
        """
        board = observation.board
        reach = (observation.position, *board.neighbors(observation.position))
        walls = [
            cell
            for cell in reach
            if barrier_is_playable(
                board,
                observation.position,
                observation.role,
                cell,
                used=observation.barriers_used,
                quota=observation.max_barriers,
            )
        ]
        if prey in walls and mass >= opts["kill_mass"]:
            return prey
        surgical = sorted(cell for cell in walls if cell != prey)
        if not surgical:
            return None
        cap = int(opts["region_cap"])
        room = region_size(board, prey, observation.move_set, cap, {})

        def room_after(cell: Coord) -> int:
            return region_size(board.with_barrier(cell), prey, observation.move_set, cap, {})

        best = min(surgical, key=lambda cell: (room_after(cell), cell))
        if room - room_after(best) >= opts["gain_min"]:
            return best
        return None

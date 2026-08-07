"""uoh-sqak's pursuer as an arena arm (M7-46) — ⚑ thief repo, opponent model only.

Modelled from their PUBLISHED brain at github.com/salah-dev-stu/uoh-sqak-cop
(`src/cipherchase/strategy/apex_cop.py`, (c) 2026 uoh-sqak — Salah Qadah, Andalus
Kalash), the cop that won all three thief sub-games of the 2026-08-07 friendly. Values
are the ones they FIELD in `config/police/game.toml [strategy]`, not class defaults.

Their objective is one line: pick the (step, wall) pair that minimises the thief's best
ESCAPE VALUE — reachable area, plus gap to the cop, plus room from the walls — where the
thief's reply is drawn from an ensemble of three archetypes. Reachable area dominates
(it reaches 49 where the other terms reach single digits), so the arm is really an
area-strangler, and that is the pressure our roster otherwise lacks: `ref-police` walls
the cell of the step it forgoes, and `SealerPoliceBrain` only walls a nearly-enclosed
cell, so neither ever strangles open board.

⚑ UPDATED at `d07b654` (2026-08-07 19:29Z). The friendly's cop moved AND walled in the
same turn — a barrier on 13 of 14 turns while their cop walked (0,0) -> (0,4) — which
chapter 3's Barrier Law does not grant. We raised it; they fixed it at the one place
every brain's decision passes through, rewrote `_best_response` to compare a step and a
wall as genuine alternatives, and retuned (`min_gain` 1 -> 2, `apex_barrier_cost` 0 ->
1.0) because a wall that deletes a single cell is never worth a turn. Their own note:
"at 0 the cop walls every turn and never closes — it caught nothing at all in 40 seeded
games", which is our own measurement of the same thing.

**So this arm now matches their turn law.** One divergence is left, and it still makes
the arm weaker than the live cop: their L3 is a depth-8 alpha-beta that PROVES a forced
capture, and it played the last two turns of every sub-game we lost. It is left out
rather than faked. The pre-fix build, and the measurement that motivated raising it,
are preserved in `docs/evidence/m7-46-sqak-thief.md`.
"""

from __future__ import annotations

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import STAY, Board, Coord
from copthief_core.domain.rules import is_legal_barrier, legal_moves
from copthief_core.strategy.brains import BrainBase, Observation
from copthief_core.strategy.decision import Decision
from copthief_core.strategy.region import region_size

__all__ = ["APEX_DEFAULTS", "SqakApexPoliceBrain"]

APEX_DEFAULTS: dict[str, float] = {
    "apex_w_reach": 1.0,  # their `apex_w_reach` — the term that dominates
    "apex_w_dist": 0.6,  # their `apex_w_dist`
    "apex_w_wall": 0.8,  # their `apex_w_wall`
    "apex_barrier_topk": 3.0,  # walls considered per turn, best area-gain first
    "apex_min_gain": 2.0,  # FIELDED at d07b654 (1 -> 2): a wall costs a turn
    "apex_barrier_cost": 1.0,  # FIELDED at d07b654: the tempo a wall must beat
    "apex_region_cap": 49.0,  # their `reachable_cells` is uncapped on a 7x7
}


def _wall_dist(board: Board, cell: Coord) -> int:
    """Their `endgame.wall_dist` — steps to the nearest board edge."""
    low = board.axis_start_index
    high = low + board.grid_size - 1
    return min(cell[0] - low, high - cell[0], cell[1] - low, high - cell[1])


class SqakApexPoliceBrain(BrainBase):
    """Their `ApexCop` L2 best-response, under our turn law (Input: the police
    Observation + our belief over the thief; Output: a step or a wall, never both)."""

    def _opts(self) -> dict[str, float]:
        return {**APEX_DEFAULTS, **self._options}

    def _escape_value(
        self, board: Board, cop: Coord, thief: Coord, move_set: tuple[str, ...]
    ) -> float:
        """Their `escape_value`: how free the thief is at `thief` with the cop at `cop`."""
        opts = self._opts()
        area = region_size(board, thief, move_set, int(opts["apex_region_cap"]), {})
        gap = abs(cop[0] - thief[0]) + abs(cop[1] - thief[1])
        return (
            opts["apex_w_reach"] * area
            + opts["apex_w_dist"] * gap
            + opts["apex_w_wall"] * _wall_dist(board, thief)
        )

    def _replies(
        self, board: Board, thief: Coord, cop: Coord, move_set: tuple[str, ...]
    ) -> set[Coord]:
        """Their ensemble = thief_v1 + naive_edge + still, unioned (union, so the
        `max` below is over ALL three archetypes' predicted cells)."""
        targets = [board.apply_move(thief, m) for m in legal_moves(board, thief, move_set)]
        if not targets:
            return {thief}
        best_v1 = max(
            targets,
            key=lambda t: (
                (abs(t[0] - cop[0]) + abs(t[1] - cop[1]))
                + 0.3 * sum(not board.is_blocked(n) for n in board.neighbors(t))
                - (1.0 if abs(t[0] - cop[0]) + abs(t[1] - cop[1]) <= 1 else 0.0)
            ),
        )
        low = board.axis_start_index
        high = low + board.grid_size - 1
        corners = [(low, low), (low, high), (high, low), (high, high)]
        goal = max(corners, key=lambda c: abs(c[0] - cop[0]) + abs(c[1] - cop[1]))
        edge = min(targets, key=lambda t: abs(t[0] - goal[0]) + abs(t[1] - goal[1]))
        return {best_v1, edge, thief}  # "still" is the thief standing its ground

    def _worst_escape(
        self, board: Board, cop: Coord, thief: Coord, move_set: tuple[str, ...]
    ) -> float:
        return max(
            self._escape_value(board, cop, r, move_set)
            for r in self._replies(board, thief, cop, move_set)
        )

    def _walls(self, observation: Observation, thief: Coord) -> list[Coord]:
        """Their `_topk_barriers`: adjacent open cells, best area-gain first."""
        opts = self._opts()
        board, cap = observation.board, int(opts["apex_region_cap"])
        base = region_size(board, thief, observation.move_set, cap, {})
        scored = []
        for cell in board.neighbors(observation.position):
            if not is_legal_barrier(
                board,
                observation.position,
                cell,
                barriers_used=observation.barriers_used,
                max_barriers=observation.max_barriers,
            ):
                continue
            gain = base - region_size(
                board.with_barrier(cell), thief, observation.move_set, cap, {}
            )
            if gain >= opts["apex_min_gain"]:
                scored.append((-gain, cell))
        scored.sort()
        return [cell for _, cell in scored[: int(opts["apex_barrier_topk"])]]

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        thief = belief.argmax()
        board = observation.board
        candidates = sorted(legal_moves(board, observation.position, observation.move_set))
        if not candidates:
            return STAY
        return min(
            candidates,
            key=lambda m: (
                self._worst_escape(
                    board, board.apply_move(observation.position, m), thief, observation.move_set
                ),
                m,
            ),
        )

    def _decide(self, observation: Observation, belief: BeliefFilter) -> Decision:
        """Their objective over BOTH action families, then our turn law picks one."""
        thief = belief.argmax()
        board, move_set = observation.board, observation.move_set
        move = self._pick_move(observation, belief)
        best_step = self._worst_escape(
            board, board.apply_move(observation.position, move), thief, move_set
        )
        cost = self._opts()["apex_barrier_cost"]
        best_wall, wall_cell = float("inf"), None
        for cell in self._walls(observation, thief):
            value = (
                self._worst_escape(board.with_barrier(cell), observation.position, thief, move_set)
                + cost
            )
            if value < best_wall:
                best_wall, wall_cell = value, cell
        if wall_cell is not None and best_wall < best_step:
            return Decision(barrier=wall_cell)
        return Decision(move=move)

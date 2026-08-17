"""bestteam's thief as an arena arm (M13p2, ADR-0017).

Re-derived from their PUBLIC repo (github.com/Diana-Koroblov/bestteam-thief, HEAD
a59fa05 — `thief/advanced.py:AdvancedThief`; members Itay Malich, Diana Koroblov)
per the ADR-0011 method: a REIMPLEMENTATION against our seam, no code copied, their
shipped `[strategy]` values as the option table. Validated against the 2026-08-16
friendly tapes (docs/evidence/m13p2-bestteam-mimic.md) — the fidelity number there
bounds every claim made with this arm.

Their policy, as studied: candidates in order STAY, N, S, E, W; root score =
value_of(dest, depth 2) - weight_scent * own-trail intensity at dest; value_of =
belief[dest]*CAPTURED + (1-belief[dest]) * lookahead over the destination-masked,
renormalized, predict-spread belief; leaf = `bestteam_eval.evaluate`. Ties within
tie_epsilon keep candidate order and draw seeded (their RNG fires 1-3x/game — the
brain is near-deterministic; trail avoidance breaks most ties). One live mode: the
trail-driven wanderer (the g02 "camp" was our completed rule-47 cage — forced).
No corner term exists — avoidance is the room term; no claim-reading exists.
GOLDEN FIDELITY (their code's own per-step scores as oracle, 70 steps): tie-aware
move agreement 57/70 = 81%, mean score deviation 5.4, divergence concentrated at
wall-adjacent states — BELOW the 90% bar, so every arena number measured against
this arm is DIRECTIONAL, stated wherever used (ADR-0017).
"""

from __future__ import annotations

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import STAY, Board, Coord
from copthief_core.strategy.bestteam_eval import evaluate
from copthief_core.strategy.brains import BrainBase, Observation

__all__ = ["THIEF_DEFAULTS", "BestteamThiefBrain"]

THIEF_DEFAULTS: dict[str, float] = {
    "weight_capture_risk": 400.0,  # their shipped [strategy] table, HEAD a59fa05
    "weight_seal_pressure": 25.0,
    "weight_room": 2.0,
    "weight_cycle": 30.0,
    "weight_scent": 4.0,
    "weight_distance": 1.0,
    "tie_epsilon": 0.1,
    "search_depth": 2.0,
    "reach_horizon": 5.0,
    "captured_value": -1000.0,
}

_ORDER = (STAY, "N", "S", "E", "W")  # their candidate insertion order (load-bearing)


class BestteamThiefBrain(BrainBase):
    """Belief-masked expectimax evader with trail-avoidance (their AdvancedThief)."""

    def _opts(self) -> dict[str, float]:
        return {**THIEF_DEFAULTS, **self._options}

    @staticmethod
    def _predict(belief: dict[Coord, float], board: Board) -> dict[Coord, float]:
        """Their filter's between-ply spread: each cell's mass uniform over its open
        neighbours (the golden-fixture variant search's best fit) — the deeper ply
        sees approaching mass, which is what prices flight from a nearing cop."""
        spread: dict[Coord, float] = {}
        for cell, mass in belief.items():
            dests = [n for n in board.neighbors(cell) if not board.is_blocked(n)] or [cell]
            share = mass / len(dests)
            for dest in dests:
                spread[dest] = spread.get(dest, 0.0) + share
        return spread

    def _value_of(
        self,
        dest: Coord,
        belief: dict[Coord, float],
        board: Board,
        walls_left: int,
        depth: int,
        opts: dict[str, float],
    ) -> float:
        caught = belief.get(dest, 0.0)
        survivors = {c: m for c, m in belief.items() if c != dest}
        total = sum(survivors.values())
        if total <= 0.0:
            return opts["captured_value"]
        survivors = {c: m / total for c, m in survivors.items()}
        if depth <= 1:
            ahead = evaluate(dest, survivors, board, walls_left, opts)
        else:
            spread = self._predict(survivors, board)
            ahead = max(
                self._value_of(nxt, spread, board, walls_left, depth - 1, opts)
                for nxt in self._dests(board, dest)
            )
        return caught * opts["captured_value"] + (1.0 - caught) * ahead

    @staticmethod
    def _dests(board: Board, cell: Coord) -> list[Coord]:
        out = [cell]  # STAY first — their options() order
        for move in _ORDER[1:]:
            dest = board.apply_move(cell, move)
            if dest != cell and not board.is_blocked(dest):
                out.append(dest)
        return out

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        opts = self._opts()
        board, here = observation.board, observation.position
        probs = belief.probs()
        walls_left = max(0, observation.max_barriers - len(board.barriers))
        trail = observation.own_smell
        scored: list[tuple[float, str]] = []
        for move in _ORDER:
            dest = board.apply_move(here, move)
            if move != STAY and (dest == here or board.is_blocked(dest)):
                continue
            value = self._value_of(
                dest, probs, board, walls_left, int(opts["search_depth"]), opts
            ) - opts["weight_scent"] * float(trail.get(f"{dest[0]},{dest[1]}", 0.0))
            scored.append((value, move))
        best = max(value for value, _ in scored)
        near = [move for value, move in scored if best - value <= opts["tie_epsilon"]]
        if len(near) <= 1:
            return near[0]
        return near[self._rng.randrange(len(near))]

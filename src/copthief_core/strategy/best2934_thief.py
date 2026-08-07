"""best2934's evader as an arena arm (M7-45).

Modelled from their PUBLISHED brain at github.com/Krayz1a/best2934-cop
(`src/p2pchase/domain/thief_brain.py`, MIT License, (c) 2026 best2934 — Tomer Levy,
Eyal Koloshi, Alon Issman), linked from kit issue #45/#48. Same practice as M7-14's
`belief-evader` for anrbj666: a named opponent becomes an arena arm so the GA and the
champion gate measure against the policy we will actually meet, not a generic baseline.

A REIMPLEMENTATION against our seam, not a port — their `OwnState`/`Board` types have
no counterpart here — so it reproduces their *policy*, and the fidelity claim is only
as good as the tests beside it. `THIEF_DEFAULTS` carries the values they FIELD
(`config/thief/setup.json`), not their class defaults; the distinction is the
measurement fault their own ADR-025 records.

⚠ What the tests found, and why this arm is cheaper to beat than its docstring
suggests: on the negotiated 7x7 board their area, adjacency and endgame terms are all
structurally inert (see `tests/unit/strategy/test_best2934_thief.py`), so this reduces
to a greedy distance-maximiser that will not camp. The terms are kept anyway — the arm
must model what they SHIP, and a board or cap they change later would wake them up.
"""

from __future__ import annotations

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import STAY, Coord
from copthief_core.domain.rules import legal_moves
from copthief_core.strategy.belief_distance import expected_distance
from copthief_core.strategy.brains import BrainBase, Observation
from copthief_core.strategy.region import region_size

__all__ = ["THIEF_DEFAULTS", "Best2934ThiefBrain"]

THIEF_DEFAULTS: dict[str, float] = {
    "area_weight": 1.0,  # weight on open space (their shipped setup.json)
    "distance_weight": 1.2,  # weight on distance from the believed cop
    "area_scale": 0.25,  # their `area * 0.25` inside the early-game score
    "endgame_window": 4.0,  # steps from survival at which safety displaces room
    "endgame_distance_weight": 2.0,  # `distance * 2.0` once inside the window
    "endgame_area_weight": 0.05,  # the residual area term in the endgame
    "adjacency_penalty": 6.0,  # standing next to the believed cop is near-fatal
    "idle_penalty": 1.0,  # camping saturates their own scent field
    "region_cap": 60.0,  # their `reachable_area(cell, limit=60)`
}


class Best2934ThiefBrain(BrainBase):
    """Area-weighted evasion with an endgame safety switch (their `ThiefBrain`).

    Input:  the observation and our belief over the cop's cell.
    Output: the highest-scoring legal move; ties break on sorted move order.
    Setup:  `THIEF_DEFAULTS`, overridable through the arena's `brain_options`.
    """

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        opts = {**THIEF_DEFAULTS, **self._options}
        board = observation.board
        candidates = sorted(legal_moves(board, observation.position, observation.move_set))
        if not candidates:
            return STAY
        remaining = max(0, observation.survival_threshold - observation.step)
        endgame = remaining <= opts["endgame_window"]
        peak = belief.argmax()
        cache: dict[Coord, int] = {}

        def score(move: str) -> float:
            dest = board.apply_move(observation.position, move)
            distance = expected_distance(dest, belief)
            area = region_size(board, dest, observation.move_set, int(opts["region_cap"]), cache)
            if endgame:
                value = opts["endgame_distance_weight"] * distance
                value += opts["endgame_area_weight"] * area
            else:
                value = opts["distance_weight"] * distance
                value += opts["area_weight"] * (area * opts["area_scale"])
            if abs(dest[0] - peak[0]) + abs(dest[1] - peak[1]) <= 1:
                value -= opts["adjacency_penalty"]
            if move == STAY:
                value -= opts["idle_penalty"]
            return value

        return max(candidates, key=lambda m: (score(m), m))

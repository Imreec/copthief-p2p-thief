"""best2934's evader as an arena arm (M7-45; rebuilt for M12 at their 5324415).

Modelled from their PUBLISHED brain at github.com/Krayz1a/best2934-thief
(`src/p2pchase/domain/thief_brain.py`, MIT License, (c) 2026 best2934 — Tomer Levy,
Eyal Koloshi, Alon Issman), linked from kit issue #45/#48, and validated against the
2026-08-14 evening friendly logs (g02/g04/g06 — the corner-runner script is GONE).
A REIMPLEMENTATION against our seam, not a port: it reproduces their *policy*, and
the fidelity claim is only as good as the tests beside it.

What changed at 5324415 (their #45 disclosure, confirmed by offline study of their
public code): an exit-counting veto chain now runs BEFORE the M7-45 score —
(1) never enter a zero-exit cell; (2) refuse ENTERING a cell with `exit_min_safe`
or fewer ways out while any alternative exists (a corner is the canonical refusal);
(3) LEAVE a one-exit seat rather than stand in it. Exits count only in-bounds
unblocked orthogonal neighbours — deliberately cop-blind and partition-blind, which
is the exploitable gap their own measure (59-60/60 survival vs their waller) hides.
Entry-veto scope: "refuses a cell" is about entry, so STAY in a two-exit seat is
allowed (the g04/g06 step-11 stand under our (6,4) wall pins this reading).
Ties resolve by their strict first-wins argmax in board move order N > S > E > W >
STAY — not alphabetically (the old arm's measurable drift).
"""

from __future__ import annotations

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import STAY, Board, Coord
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
    "exit_min_safe": 2.0,  # veto: never ENTER a cell with this few ways out
}

_MOVE_ORDER = {"N": 0, "S": 1, "E": 2, "W": 3, STAY: 4}


def _exits(board: Board, cell: Coord) -> int:
    """Ways out of `cell`: in-bounds unblocked orthogonal neighbours (cop-blind)."""
    return sum(1 for n in board.neighbors(cell) if not board.is_blocked(n))


def _survivable(
    board: Board, position: Coord, candidates: list[str], dests: dict[str, Coord], exit_min: float
) -> list[str]:
    """Their veto chain; every veto falls back rather than empty the candidate set."""
    kept = [m for m in candidates if _exits(board, dests[m]) > 0]
    candidates = kept or candidates
    kept = [m for m in candidates if m == STAY or _exits(board, dests[m]) > exit_min]
    candidates = kept or candidates
    if _exits(board, position) <= 1:
        kept = [m for m in candidates if m != STAY]
        candidates = kept or candidates
    return candidates


class Best2934ThiefBrain(BrainBase):
    """Exit-veto chain, then area-weighted evasion with an endgame safety switch.

    Input:  the observation and our belief over the cop's cell.
    Output: the surviving highest-scoring move; ties break in their N>S>E>W>STAY order.
    Setup:  `THIEF_DEFAULTS`, overridable through the arena's `brain_options`.
    """

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        opts = {**THIEF_DEFAULTS, **self._options}
        board = observation.board
        candidates = sorted(legal_moves(board, observation.position, observation.move_set))
        if not candidates:
            return STAY
        dests = {m: board.apply_move(observation.position, m) for m in candidates}
        candidates = _survivable(
            board, observation.position, candidates, dests, opts["exit_min_safe"]
        )
        remaining = max(0, observation.survival_threshold - observation.step)
        endgame = remaining <= opts["endgame_window"]
        peak = belief.argmax()
        cache: dict[Coord, int] = {}

        def score(move: str) -> float:
            dest = dests[move]
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

        return max(candidates, key=lambda m: (score(m), -_MOVE_ORDER[m]))

"""bestteam thief evaluation terms (M13p2, ADR-0017) — arena-arm support.

Re-derived from the offline study of their PUBLIC repos (github.com/Diana-Koroblov/
bestteam-thief, HEAD a59fa05; members Itay Malich, Diana Koroblov — their own
rule-49-style disclosure), ADR-0011 method: policy re-implemented against OUR seam,
no code copied; constants are their shipped `[strategy]` values, carried as the
arm's option table in `bestteam_thief.py`. Fidelity is only as good as the tape
validation beside it (docs/evidence/m13p2-bestteam-mimic.md).

Their evaluate(cell), higher = better for the thief:
    -400*capture_risk - 25*seal_pressure + 2*|reach_5| + 30*has_cycle + 1*E[dist]
Pure geometry — no I/O, no clock, no RNG.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping

from copthief_core.domain.board import Board, Coord

__all__ = ["capture_risk", "evaluate", "k_step_reach", "region_has_cycle", "seal_pressure"]


def _open_neighbors(board: Board, cell: Coord) -> list[Coord]:
    return [n for n in board.neighbors(cell) if not board.is_blocked(n)]


def capture_risk(cell: Coord, belief: Mapping[Coord, float], board: Board) -> float:
    """Their risk term: cop mass that could seal `cell` this turn — mass on the cell
    itself or orthogonally adjacent; a one-exit cell also counts mass that can reach
    its last exit. No passable neighbour at all risks the whole mass."""
    exits = _open_neighbors(board, cell)
    if not exits:
        return sum(belief.values())
    targets = {cell}
    if len(exits) == 1:
        targets.add(exits[0])
    risk = 0.0
    for cop, mass in belief.items():
        if any(cop == t or abs(cop[0] - t[0]) + abs(cop[1] - t[1]) == 1 for t in targets):
            risk += mass
    return risk


def seal_pressure(cell: Coord, board: Board, walls_left: int) -> float:
    """Their seal term: how affordably the remaining quota closes this cell's exits."""
    needed = max(len(_open_neighbors(board, cell)) - 1, 0)
    if walls_left <= 0 or needed > walls_left:
        return 0.0
    return 1.0 - needed / (walls_left + 1)


def k_step_reach(cell: Coord, board: Board, k: int) -> int:
    """Cells reachable within `k` orthogonal steps (their room term's BFS ball)."""
    seen = {cell}
    frontier = deque([(cell, 0)])
    while frontier:
        cur, d = frontier.popleft()
        if d == k:
            continue
        for n in _open_neighbors(board, cur):
            if n not in seen:
                seen.add(n)
                frontier.append((n, d + 1))
    return len(seen)


def region_has_cycle(cell: Coord, board: Board) -> bool:
    """Their cycle term: the reachable region holds a cycle (edges >= vertices)."""
    seen = {cell}
    frontier = deque([cell])
    edges = 0
    while frontier:
        cur = frontier.popleft()
        for n in _open_neighbors(board, cur):
            edges += 1  # each undirected edge counted twice across the sweep
            if n not in seen:
                seen.add(n)
                frontier.append(n)
    return (edges // 2) >= len(seen)


def _bfs_distance(board: Board, src: Coord, dst: Coord, cap: int) -> int:
    if src == dst:
        return 0
    seen = {src}
    frontier = deque([(src, 0)])
    while frontier:
        cur, d = frontier.popleft()
        for n in _open_neighbors(board, cur):
            if n == dst:
                return d + 1
            if n not in seen:
                seen.add(n)
                frontier.append((n, d + 1))
    return cap


def evaluate(
    cell: Coord,
    belief: Mapping[Coord, float],
    board: Board,
    walls_left: int,
    weights: Mapping[str, float],
) -> float:
    """Their leaf, weights from the arm's option table (their shipped values)."""
    cap = 2 * board.grid_size
    expected_dist = sum(mass * _bfs_distance(board, cell, cop, cap) for cop, mass in belief.items())
    return (
        -weights["weight_capture_risk"] * capture_risk(cell, belief, board)
        - weights["weight_seal_pressure"] * seal_pressure(cell, board, walls_left)
        + weights["weight_room"] * k_step_reach(cell, board, int(weights["reach_horizon"]))
        + weights["weight_cycle"] * (1.0 if region_has_cycle(cell, board) else 0.0)
        + weights["weight_distance"] * expected_dist
    )

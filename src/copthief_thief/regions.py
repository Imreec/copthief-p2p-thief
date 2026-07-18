"""Two-front region analysis (PRD_thief_brain §3): the territory we still own.

`safe_region_size` counts the cells we reach strictly before the cop can (barrier-
aware BFS race from both fronts) — the region-survival core: prefer the move that
keeps the largest territory ours.
"""

from __future__ import annotations

from collections import deque

from copthief_core.domain.board import Board, Coord


def bfs_distances(
    board: Board, start: Coord, move_set: tuple[str, ...], cap: int
) -> dict[Coord, int]:
    """Step distances over open cells from `start` (capped breadth-first search)."""
    if board.is_blocked(start):
        return {}
    distances = {start: 0}
    frontier = deque([start])
    while frontier and len(distances) < cap:
        cell = frontier.popleft()
        for move in move_set:
            dest = board.apply_move(cell, move)
            if dest not in distances and not board.is_blocked(dest):
                distances[dest] = distances[cell] + 1
                frontier.append(dest)
    return distances


def region_size(board: Board, start: Coord, move_set: tuple[str, ...], cap: int) -> int:
    """Size of the open region reachable from `start` (capped)."""
    return len(bfs_distances(board, start, move_set, cap))


def safe_region_size(
    board: Board, ours: Coord, cop: Coord, move_set: tuple[str, ...], cap: int
) -> int:
    """Cells we reach strictly before the cop (unreachable-to-cop counts as ours)."""
    our_front = bfs_distances(board, ours, move_set, cap)
    cop_front = bfs_distances(board, cop, move_set, cap)
    return sum(
        1 for cell, our_distance in our_front.items() if our_distance < cop_front.get(cell, cap + 1)
    )

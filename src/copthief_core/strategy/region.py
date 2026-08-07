"""Reachable-region query shared by pursuit and evasion (M7-14).

Moved from the police role package: the cop's barrier surgery and the trap-aware
evader's wall forecast are the same geometric question — how much open board remains
reachable from a cell — and CLAUDE.md #11 forbids two copies of it.
"""

from __future__ import annotations

from collections import deque

from copthief_core.domain.board import Board, Coord

__all__ = ["path_length", "region_size"]


def region_size(
    board: Board, start: Coord, move_set: tuple[str, ...], cap: int, cache: dict[Coord, int]
) -> int:
    """Size of the open region reachable from `start` (capped BFS; per-board cache).

    The cache is keyed by start cell and owned by the caller, which must supply a
    fresh dict per board (barrier sets differ between root actions).
    """
    if start in cache:
        return cache[start]
    if board.is_blocked(start):
        cache[start] = 0
        return 0
    seen = {start}
    frontier = [start]
    while frontier and len(seen) < cap:
        cell = frontier.pop()
        for move in move_set:
            dest = board.apply_move(cell, move)
            if dest not in seen and not board.is_blocked(dest):
                seen.add(dest)
                frontier.append(dest)
    cache[start] = len(seen)
    return len(seen)


def path_length(board: Board, start: Coord, goal: Coord, move_set: tuple[str, ...]) -> int | None:
    """Steps along the shortest open path from `start` to `goal` (BFS).

    Output: the step count, or None when no open path exists. The None case is the
    load-bearing one: it is how a cop rejects a wall that would seal it away from the
    thief it is chasing, which greedy area-shrinking would otherwise happily place.
    """
    if board.is_blocked(goal):
        return None
    if start == goal:
        return 0
    seen = {start}
    frontier: deque[tuple[Coord, int]] = deque([(start, 0)])
    while frontier:
        cell, steps = frontier.popleft()
        for move in move_set:
            dest = board.apply_move(cell, move)
            if dest in seen or board.is_blocked(dest):
                continue
            if dest == goal:
                return steps + 1
            seen.add(dest)
            frontier.append((dest, steps + 1))
    return None

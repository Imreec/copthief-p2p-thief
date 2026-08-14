"""Steady-heading interception (M11 part 2) — anrbj666's meet-the-runner rule.

Studied from the repos they shared (ADR-0011 consent basis, re-implemented, no
code copied): project a steadily-marching peak forward; at an obstacle turn to
the passable neighbor farthest from the cop (their flee-side rule, never
doubling back); the cut is the first projected cell the cop reaches no later
than the runner. Pure geometry: no I/O, no RNG, no config reads.
"""

from __future__ import annotations

from copthief_core.domain.board import Board, Coord
from copthief_core.strategy.region import path_length

__all__ = ["intercept_target"]


def intercept_target(
    board: Board,
    cop: Coord,
    peak: Coord,
    velocity: Coord,
    move_set: tuple[str, ...],
    *,
    horizon: int = 10,
) -> Coord | None:
    """First projected runner cell the cop reaches no later than the runner.

    Input: the board, the cop cell, the peak and its unit velocity.
    Output: the cut cell, or None when the runner wins every leg in `horizon`.
    """
    cell, vel, prev = peak, velocity, peak
    path: list[Coord] = []
    for _ in range(horizon):
        nxt = (cell[0] + vel[0], cell[1] + vel[1])
        if board.is_blocked(nxt):
            options = [n for n in board.neighbors(cell) if not board.is_blocked(n) and n != prev]
            if not options:
                break
            nxt = max(options, key=lambda n: (abs(n[0] - cop[0]) + abs(n[1] - cop[1]), n))
            vel = (nxt[0] - cell[0], nxt[1] - cell[1])
        path.append(nxt)
        prev, cell = cell, nxt
    for k, spot in enumerate(path, start=1):
        gap = path_length(board, cop, spot, move_set)
        if gap is not None and gap <= k:
            return spot
    return None

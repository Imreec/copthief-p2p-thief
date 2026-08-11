"""One-ply worst-wall forecast + lethal gate (M9-3) — the anti-imprisonment core.

The barrier law limits placement to the placer's cell and its orthogonal
neighbors, so the trap game is EXACTLY computable one ply ahead: for a candidate
landing, enumerate every action a cop at a hypothesized cell could take next
turn and score the worst case. Two graded instruments:

- `lethal_landing`: can ANY hypothesized cop cell END us next turn (step onto
  the landing, wall the landing — rule 46 — or a wall that imprisons it — rule
  47)? A landing that fails ranks below every landing that passes; the gate
  sits ABOVE flight distance because inside a forming seal "away from the cop"
  is measured the long way round and walks straight into the wall.
- `worst_wall_outcome`: the elementwise-worst (escapes, region) after the
  cop's best wall — the graded safety term between lethal and safe.

Belief-native by construction: callers run these from EVERY plausible support
cell and take the MIN — a kill line through any plausible cell disqualifies
(a lone stale argmax dodges phantom walls and walks into real ones). Concept
studied from anrbj666's doctrine layer (repos shared by them for study —
ADR-0011, no code copied) after the counted 30–90; re-implemented and
re-measured here. Pure geometry: no I/O, no RNG, no config reads.
"""

from __future__ import annotations

from itertools import combinations

from copthief_core.domain.board import Board, Coord
from copthief_core.domain.rules import is_imprisoned
from copthief_core.strategy.region import region_size

__all__ = ["lethal_landing", "worst_wall_outcome", "worst_walls_region"]


def _cop_reach(board: Board, cop: Coord) -> tuple[Coord, ...]:
    """The cells a cop at `cop` can wall (or step onto): own cell + open neighbors."""
    return tuple(cell for cell in (cop, *board.neighbors(cop)) if not board.is_blocked(cell))


def worst_wall_outcome(
    board: Board,
    landing: Coord,
    cop: Coord,
    move_set: tuple[str, ...],
    *,
    region_cap: int,
    quota_left: int = 1,
) -> tuple[int, int]:
    """The worst (escapes, region) the cop can inflict on `landing` with one wall.

    Input: the CURRENT board, our candidate landing, one hypothesized cop cell.
    Output: lexicographic-worst (orthogonal escapes from the landing, reachable
    region from the landing) over every wall in the cop's reach — (0, 0) when the
    cop can wall the landing itself (rule 46). With no quota the baseline
    (no-wall) outcome is returned: only the step-on threat remains.
    """

    def outcome(with_board: Board) -> tuple[int, int]:
        escapes = sum(1 for n in with_board.neighbors(landing) if not with_board.is_blocked(n))
        return escapes, region_size(with_board, landing, move_set, region_cap, {})

    if quota_left <= 0:
        return outcome(board)
    outcomes = []
    for cell in _cop_reach(board, cop):
        if cell == landing:
            outcomes.append((0, 0))  # the wall lands ON us: rule-46 capture
            continue
        outcomes.append(outcome(board.with_barrier(cell)))
    return min(outcomes) if outcomes else outcome(board)


def worst_walls_region(
    board: Board,
    landing: Coord,
    cop: Coord,
    move_set: tuple[str, ...],
    *,
    walls: int,
    reach: int,
) -> int:
    """The worst reachable region a stationary builder can leave `landing` in.

    Input: the CURRENT board, our candidate landing, one hypothesized cop cell,
    the wall budget to credit (`walls` — callers clamp to the live quota) and the
    builder's Manhattan `reach` (1 = the barrier law's own-cell-plus-neighbors;
    2 credits one walk step between investments). Output: the minimum uncapped
    region from `landing` over every wall SET of that size — a cage is priced
    while its gap still exists, not one wall before it closes (M11-1; the M10
    exposure was exactly this blindness). Walls on the landing itself are the
    rule-46 kill line and belong to `lethal_landing`, not here. NB a landing-
    distance site prune was tried for speed and REVERTED: it erased all four
    signed-start survivals vs police-m10 — distant walls close the LARGE
    forming cages that a persistent builder still converts. Batch callers use
    `worst_walls_regions` (same semantics, one scan for many landings).
    """
    return worst_walls_regions(board, [landing], cop, move_set, walls=walls, reach=reach)[landing]


def worst_walls_regions(
    board: Board,
    landings: list[Coord],
    cop: Coord,
    move_set: tuple[str, ...],
    *,
    walls: int,
    reach: int,
) -> dict[Coord, int]:
    """`worst_walls_region` for many landings in one combo scan (per-board BFS
    cache shared across landings — the affordability fix for the armed arena)."""
    cap = board.grid_size * board.grid_size
    low = board.axis_start_index
    span = range(low, low + board.grid_size)
    sites = [
        (r, c)
        for r in span
        for c in span
        if abs(r - cop[0]) + abs(c - cop[1]) <= reach and not board.is_blocked((r, c))
    ]
    base_cache: dict[Coord, int] = {}
    worst = {cell: region_size(board, cell, move_set, cap, base_cache) for cell in landings}
    count = min(walls, len(sites))
    if count <= 0:
        return worst
    for combo in combinations(sites, count):
        candidate = board
        for cell in combo:
            candidate = candidate.with_barrier(cell)
        cache: dict[Coord, int] = {}
        for cell in landings:
            # A wall ON a landing is the rule-46 kill line (lethal gate's job),
            # so a combo containing this landing does not price it here.
            if cell not in combo and worst[cell] > 1:
                worst[cell] = min(worst[cell], region_size(candidate, cell, move_set, cap, cache))
    if count >= len(sites):
        # Tiny site sets: the only combo contained the landing itself — price
        # the per-landing equivalent (every OTHER site walled) instead.
        for cell in landings:
            if cell in set(sites) and worst[cell] > 1:
                candidate = board
                for site in sites:
                    if site != cell:
                        candidate = candidate.with_barrier(site)
                worst[cell] = min(worst[cell], region_size(candidate, cell, move_set, cap, {}))
    return worst


def lethal_landing(
    board: Board,
    landing: Coord,
    support: list[Coord],
    *,
    quota_left: int = 1,
) -> bool:
    """True iff ANY hypothesized cop cell can end the game on `landing` next turn.

    Three kill lines per support cell: step onto the landing, wall the landing
    (rule 46), or place a wall that leaves the landing imprisoned (rule 47).
    The belief-native disqualifier: one plausible kill line is enough.
    """
    for cop in support:
        reach = _cop_reach(board, cop)
        if landing in reach:  # step-on capture, or the rule-46 wall
            return True
        if quota_left <= 0:
            continue
        for cell in reach:
            if cell != landing and is_imprisoned(board.with_barrier(cell), landing):
                return True
    return False

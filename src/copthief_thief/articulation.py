"""Articulation trap-awareness (PRD_thief_brain §3): the counter to graph surgery.

Tarjan articulation points over the open-cell grid graph mark where ONE well-placed
barrier disconnects territory. A destination that ends up in a small component after
such a cut is a pocket the sibling brain's surgery would love to seal — penalized
while the cop's quota can still pay for it.
"""

from __future__ import annotations

from copthief_core.domain.board import Board, Coord
from copthief_thief.regions import bfs_distances, region_size


def articulation_points(
    board: Board, seed: Coord, move_set: tuple[str, ...], cap: int
) -> tuple[Coord, ...]:
    """Articulation cells of the open component containing `seed` (iterative Tarjan).

    The component is walked in FULL (board-bounded, never `cap`-truncated — Tarjan
    over a truncated graph would invent or miss cuts); `cap` only bounds the later
    sealed-component measurements.
    """
    del cap  # articulation needs the whole component; the board bounds it already
    full = board.grid_size * board.grid_size
    members = set(bfs_distances(board, seed, move_set, full))
    if not members:
        return ()
    component = sorted(members)
    neighbors = {
        cell: [
            board.apply_move(cell, move)
            for move in move_set
            if board.apply_move(cell, move) != cell and board.apply_move(cell, move) in members
        ]
        for cell in component
    }
    index: dict[Coord, int] = {}
    low: dict[Coord, int] = {}
    parent: dict[Coord, Coord | None] = {}
    cut: set[Coord] = set()
    counter = 0
    for root in component:
        if root in index:
            continue
        parent[root] = None
        stack: list[tuple[Coord, int]] = [(root, 0)]
        root_children = 0
        while stack:
            cell, pointer = stack[-1]
            if cell not in index:
                index[cell] = low[cell] = counter
                counter += 1
            if pointer < len(neighbors[cell]):
                stack[-1] = (cell, pointer + 1)
                nxt = neighbors[cell][pointer]
                if nxt not in index:
                    parent[nxt] = cell
                    if cell == root:
                        root_children += 1
                    stack.append((nxt, 0))
                elif nxt != parent[cell]:
                    low[cell] = min(low[cell], index[nxt])
            else:
                stack.pop()
                up = parent[cell]
                if up is not None:
                    low[up] = min(low[up], low[cell])
                    if up != root and low[cell] >= index[up]:
                        cut.add(up)
        if root_children > 1:
            cut.add(root)
    return tuple(sorted(cut))


def min_sealed_component(
    board: Board,
    dest: Coord,
    cuts: tuple[Coord, ...],
    move_set: tuple[str, ...],
    cap: int,
) -> int:
    """The smallest region `dest` lands in after ONE articulation cell is walled
    (`cap` when no cut can separate it — an open destination)."""
    smallest = cap
    for cut in cuts:
        if cut == dest:
            continue
        sealed = region_size(board.with_barrier(cut), dest, move_set, cap)
        smallest = min(smallest, sealed)
    return smallest

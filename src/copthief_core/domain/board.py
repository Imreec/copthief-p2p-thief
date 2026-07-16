"""Board geometry (book ch.3 §3.3): discrete square grid, axis contract, barriers.

Input: the negotiated axis parameters and barrier set; Output: pure geometric queries.
The compass moves N/S/E/W are board-frame directions — how they map onto (row, col)
depends on the signed axis contract (`axis_origin_corner`, `axis_start_index`), which is
why the deltas are derived here and nowhere else.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

Coord = tuple[int, int]

STAY = "STAY"
# Deltas in the reference frame (origin at the top-left corner, rows growing downward).
_TOP_LEFT_DELTAS: dict[str, Coord] = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "W": (0, -1)}


@dataclass(frozen=True)
class Board:
    """Immutable board: grid side, axis contract, and the barrier set placed so far."""

    grid_size: int
    axis_origin_corner: str
    axis_start_index: int
    barriers: frozenset[Coord] = frozenset()

    def move_delta(self, move: str) -> Coord:
        """(d_row, d_col) for a compass move under the negotiated axis origin.

        Raises ValueError on a move outside the orthogonal set — diagonals and typos
        surface immediately instead of corrupting a position.
        """
        if move == STAY:
            return (0, 0)
        if move not in _TOP_LEFT_DELTAS:
            raise ValueError(f"unknown move: {move!r}")
        d_row, d_col = _TOP_LEFT_DELTAS[move]
        if self.axis_origin_corner.startswith("bottom"):
            d_row = -d_row
        if self.axis_origin_corner.endswith("right"):
            d_col = -d_col
        return (d_row, d_col)

    def apply_move(self, pos: Coord, move: str) -> Coord:
        """Destination cell of `move` from `pos` (geometry only — legality lives in rules)."""
        d_row, d_col = self.move_delta(move)
        return (pos[0] + d_row, pos[1] + d_col)

    def in_bounds(self, cell: Coord) -> bool:
        """True iff both indices lie in [axis_start_index, axis_start_index + grid_size)."""
        low = self.axis_start_index
        high = low + self.grid_size
        return low <= cell[0] < high and low <= cell[1] < high

    def is_blocked(self, cell: Coord) -> bool:
        """True iff the cell cannot be occupied: a barrier, or off the board entirely."""
        return not self.in_bounds(cell) or cell in self.barriers

    def with_barrier(self, cell: Coord) -> Board:
        """A new board with `cell` barricaded (barriers are irreversible — book ch.3 §3.4)."""
        return replace(self, barriers=self.barriers | {cell})

    def neighbors(self, cell: Coord) -> tuple[Coord, ...]:
        """The in-bounds orthogonal neighbors of `cell` (barriers NOT filtered here)."""
        candidates = (
            (cell[0] + d_row, cell[1] + d_col) for d_row, d_col in _TOP_LEFT_DELTAS.values()
        )
        return tuple(c for c in candidates if self.in_bounds(c))

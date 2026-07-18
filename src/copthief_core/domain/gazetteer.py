"""Gazetteer (TODO M3-4; PLAN §8): the signed map_area's landmarks on the signed grid.

Our PRIVATE reading of `world.map_area` — never negotiated, never crosses the wire.
Anchors are fractional so one payload resolves onto whatever grid size was signed.
The parser is a CLOSED vocabulary: opponent text (adversarial input, App E) can only
ever map to a known landmark or to None — it is matched, never executed, never
forwarded (the LLM-never-decides rule extends to hints carrying instructions).
Pure — no I/O; the payload dict arrives loaded (shared/config.load_gazetteer).
"""

from __future__ import annotations

from typing import Any

from copthief_core.domain.board import Board, Coord


class Gazetteer:
    """Landmark → cells resolution + closed-world hint parsing (Input: resolved map)."""

    def __init__(self, landmarks: dict[str, tuple[Coord, ...]]) -> None:
        self._landmarks = dict(landmarks)

    @classmethod
    def from_payload(cls, payload: dict[str, Any], *, map_area: str, board: Board) -> Gazetteer:
        """Resolve an area's fractional anchors onto `board` (Chebyshev balls, clipped).

        An unknown map_area yields an EMPTY closed world — parsing then always returns
        None and composition refuses loudly, instead of inventing geography.
        """
        area = payload.get("areas", {}).get(map_area, {})
        low = board.axis_start_index
        span = board.grid_size - 1
        landmarks: dict[str, tuple[Coord, ...]] = {}
        for name, anchor in area.get("landmarks", {}).items():
            row = low + round(float(anchor["row_frac"]) * span)
            col = low + round(float(anchor["col_frac"]) * span)
            radius = int(anchor["radius"])
            cells = tuple(
                (r, c)
                for r in range(row - radius, row + radius + 1)
                for c in range(col - radius, col + radius + 1)
                if board.in_bounds((r, c))
            )
            landmarks[str(name)] = cells
        return cls(landmarks)

    def landmarks(self) -> tuple[str, ...]:
        """The closed vocabulary, sorted for determinism."""
        return tuple(sorted(self._landmarks))

    def cells_for(self, landmark: str) -> tuple[Coord, ...]:
        """The board cells a landmark implies (empty for unknown names)."""
        return self._landmarks.get(landmark, ())

    def parse(self, text: str, *, max_words: int) -> str | None:
        """Closed-world match: the longest landmark named within the first `max_words`
        words of `text` (case-insensitive substring), or None. Total — never raises
        on any input, which is the whole injection-safety contract."""
        if not isinstance(text, str) or not text:
            return None
        window = " ".join(text.split()[:max_words]).casefold()
        best: str | None = None
        for name in sorted(self._landmarks):
            if name.casefold() in window and (best is None or len(name) > len(best)):
                best = name
        return best

    def _min_distance(self, landmark: str, position: Coord) -> int:
        return min(
            abs(position[0] - r) + abs(position[1] - c) for r, c in self._landmarks[landmark]
        )

    def nearest(self, position: Coord) -> str:
        """The landmark closest to `position` (Manhattan; ties break lexicographically)."""
        return min(self._landmarks, key=lambda n: (self._min_distance(n, position), n))

    def farthest(self, position: Coord) -> str:
        """The landmark farthest from `position` — the lie mechanism's pick (M5 times it)."""
        return min(self._landmarks, key=lambda n: (-self._min_distance(n, position), n))

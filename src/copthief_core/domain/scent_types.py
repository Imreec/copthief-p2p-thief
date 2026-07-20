"""Shared type aliases for the scent layer (kept apart so the model modules never
import each other — `scent_models` owns the protocol, `scent_book` the deviation).
"""

from __future__ import annotations

from typing import Any

from copthief_core.domain.board import Coord

Cells = dict[Coord, float]
InBounds = Any  # Callable[[Coord], bool]; kept loose so the field owns bounds policy.

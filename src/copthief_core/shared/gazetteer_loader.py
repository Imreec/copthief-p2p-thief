"""Gazetteer file loading (M3-4), split from shared/config (150-line rule)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from copthief_core.domain.board import Board
from copthief_core.domain.gazetteer import Gazetteer


def load_gazetteer(path: Path, *, map_area: str, board: Board) -> Gazetteer:
    """Private landmark payload resolved onto the signed board; a missing file or
    unknown area yields an EMPTY gazetteer (hint layer falls back, never invents)."""
    if not path.exists():
        return Gazetteer.from_payload({}, map_area=map_area, board=board)
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return Gazetteer.from_payload(payload, map_area=map_area, board=board)

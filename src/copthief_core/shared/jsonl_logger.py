"""JSONL runtime log (PLAN §7): one canonical-JSON record per event, append-only.

The log carries wire dicts VERBATIM (re-serialized with the protocol's canonical dumps
settings), so replay can re-derive every hash from the log alone — it feeds replay (M4),
the belief overlay, profiling, and disputes. `seq` makes truncation visible.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonlEventLogger:
    """Append-only event writer; a fresh instance continues an existing file's sequence."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._seq = len(read_events(path)) if path.exists() else 0

    def log(self, event: dict[str, Any]) -> None:
        """Append one event (Input: a JSON-serializable dict; `seq` is stamped here)."""
        self._seq += 1
        record = {"seq": self._seq, **event}
        line = json.dumps(record, ensure_ascii=False, sort_keys=True)
        with self._path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")


def read_events(path: Path) -> list[dict[str, Any]]:
    """All events in file order (Input: log path; Output: parsed dicts)."""
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events

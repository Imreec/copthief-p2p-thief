"""M6-7 watchdog (FR-8; PLAN §10): stall -> persist snapshot -> controlled shutdown.

Deterministic core on a fake clock (`check()` driven directly, no thread); the
threaded path is exercised by the chaos drill. A stall is never a silent freeze:
the snapshot lands on disk and the shutdown callback fires exactly once.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from copthief_core.peer.session import PeerSession
from copthief_core.peer.watchdog import Watchdog, session_snapshot
from copthief_core.shared.config import load_all

CONSTITUTION, _SHIPPED, _LIMITS = load_all(Path("config"), counted=False)
PRIVATE = replace(_SHIPPED, police_class="random", thief_class="random")


def make_watchdog(tmp_path: Path, *, timeout: float = 10.0) -> tuple[Watchdog, list[str]]:
    stalls: list[str] = []
    dog = Watchdog(
        timeout_sec=timeout,
        # The I/O budget is exercised by test_watchdog_io_window (M7-7(1)); these cases
        # never enter a window, so the loop-liveness budget is the one under test.
        io_timeout_sec=timeout * 4,
        snapshot=lambda: {"role": "police", "step": 3},
        persist_path=tmp_path / "state" / "state_uid-1.json",
        on_stall=stalls.append,
    )
    return dog, stalls


def test_a_beating_loop_never_fires(tmp_path: Path) -> None:
    dog, stalls = make_watchdog(tmp_path)
    dog.beat(now=0.0)
    assert dog.check(now=9.0) is False
    dog.beat(now=9.0)
    assert dog.check(now=18.0) is False
    assert stalls == []
    assert dog.fired is False


def test_a_stalled_loop_persists_the_snapshot_and_shuts_down_once(tmp_path: Path) -> None:
    dog, stalls = make_watchdog(tmp_path)
    dog.beat(now=0.0)
    assert dog.check(now=10.5) is True
    assert dog.fired is True
    assert len(stalls) == 1
    assert "stall" in stalls[0]
    written = json.loads((tmp_path / "state" / "state_uid-1.json").read_text(encoding="utf-8"))
    assert written == {"role": "police", "step": 3}
    # A second check never re-fires (controlled shutdown happens exactly once).
    assert dog.check(now=99.0) is False
    assert len(stalls) == 1


def test_session_snapshot_carries_the_resumable_facts() -> None:
    police = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=1)
    snapshot = session_snapshot(police)
    assert snapshot["role"] == "police"
    assert snapshot["state"] == police.machine.state.value
    assert snapshot["steps_sealed"] == 0
    assert snapshot["position"] == list(police.position)
    assert snapshot["outcome"] is None
    json.dumps(snapshot)  # persistable as-is

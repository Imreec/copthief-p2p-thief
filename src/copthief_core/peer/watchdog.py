"""Watchdog (M6-7; FR-8; PLAN §10): a stalled loop is never a silent freeze.

Monitors the peer loop's heartbeat; silence past the signed `watchdog_timeout_sec`
persists a state snapshot (git-ignored operational artifact, PRD_gatekeeper §7 D4)
and fires the controlled-shutdown callback EXACTLY once. The deterministic core
(`beat`/`check` with explicit times) is unit-tested on a fake clock; `start()`
adds the real thread (guidelines §15: threads only at watchdog/inbox seams).
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any


def session_snapshot(session: Any) -> dict[str, Any]:  # noqa: ANN401 - PeerSession (no import cycle)
    """The resumable facts of a session (Input: a PeerSession; Output: JSON-safe
    dict — machine state, own truth, sealing progress; never opponent secrets)."""
    return {
        "game_uid": session.game_uid,
        "role": session.role,
        "state": session.machine.state.value,
        "steps_sealed": len(session.records),
        "position": list(session.position),
        "barriers": sorted(list(b) for b in session.board.barriers),
        "outcome": session.outcome,
    }


class Watchdog:
    """Heartbeat monitor with persist-then-shutdown semantics (fires once)."""

    def __init__(
        self,
        *,
        timeout_sec: float,
        snapshot: Callable[[], dict[str, Any]],
        persist_path: Path,
        on_stall: Callable[[str], None],
    ) -> None:
        self._timeout = timeout_sec
        self._snapshot = snapshot
        self._persist_path = persist_path
        self._on_stall = on_stall
        self._last_beat: float | None = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.fired = False

    def beat(self, *, now: float | None = None) -> None:
        """The loop is alive (called every iteration; `now` injectable for tests)."""
        with self._lock:
            self._last_beat = time.time() if now is None else now

    def check(self, *, now: float | None = None) -> bool:
        """One stall check; True exactly when this call fired the shutdown."""
        with self._lock:
            if self.fired or self._last_beat is None:
                return False
            moment = time.time() if now is None else now
            if moment - self._last_beat <= self._timeout:
                return False
            self.fired = True
            silent_for = moment - self._last_beat
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        self._persist_path.write_text(
            json.dumps(self._snapshot(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self._on_stall(f"loop stall: no heartbeat for {silent_for:.2f}s (state persisted)")
        return True

    def start(self, *, poll_interval: float) -> None:
        """Arm the monitor thread (daemonic: it must never block shutdown itself)."""

        def watch() -> None:
            while not self._stop.wait(poll_interval):
                if self.check():
                    return

        self._thread = threading.Thread(target=watch, name="watchdog", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Disarm (controlled shutdown path or end of game)."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self._timeout)

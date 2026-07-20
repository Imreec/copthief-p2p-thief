"""Watchdog (M6-7; FR-8; PLAN §10): a stalled loop is never a silent freeze.

Monitors the peer loop's heartbeat; silence past the signed `watchdog_timeout_sec`
persists a state snapshot (git-ignored operational artifact, PRD_gatekeeper §7 D4)
and fires the controlled-shutdown callback EXACTLY once. The deterministic core
(`beat`/`check` with explicit times) is unit-tested on a fake clock; `start()`
adds the real thread (guidelines §15: threads only at watchdog/inbox seams).

**M7-7(1): the heartbeat measures LOOP LIVENESS, not I/O duration.** The real-tunnel
kill drill fired this watchdog on a healthy loop — a blocking outbound push held the
loop inside the transport, no beat landed, and the 60 s budget self-terminated us
before our own 180 s turn deadline could classify the opponent as silent. A deliberate,
bounded wait on the wire is not a wedge, so the loop declares it (`io_window`, applied
at the transport seam by `watched`) and the watchdog applies the reconciled I/O budget
instead — which `shared/budgets` pins strictly BEHIND the turn deadline. An I/O wait
that outlasts even that budget still fires: this is a backstop, never an off switch.
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TextIO


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
        io_timeout_sec: float,
        snapshot: Callable[[], dict[str, Any]],
        persist_path: Path,
        on_stall: Callable[[str], None],
    ) -> None:
        self._timeout = timeout_sec
        self._io_timeout = io_timeout_sec
        self._snapshot = snapshot
        self._persist_path = persist_path
        self._on_stall = on_stall
        self._last_beat: float | None = None
        self._io_since: float | None = None
        self._io_depth = 0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.fired = False

    @property
    def in_io(self) -> bool:
        """True while the loop is inside a declared blocking-transport call."""
        with self._lock:
            return self._io_depth > 0

    def beat(self, *, now: float | None = None) -> None:
        """The loop is alive (called every iteration; `now` injectable for tests)."""
        with self._lock:
            self._last_beat = time.time() if now is None else now

    def enter_io(self, *, now: float | None = None) -> None:
        """Declare a deliberate blocking wait on the transport (nestable: a handshake
        pushes and then waits, so one window may sit inside another)."""
        with self._lock:
            if self._io_depth == 0:
                self._io_since = time.time() if now is None else now
            self._io_depth += 1

    def exit_io(self, *, now: float | None = None) -> None:
        """The transport returned — only the OUTERMOST window hands the loop budget
        back, and it beats, because returning from I/O is itself proof of liveness."""
        with self._lock:
            self._io_depth = max(0, self._io_depth - 1)
            if self._io_depth == 0:
                self._io_since = None
                self._last_beat = time.time() if now is None else now

    @contextmanager
    def io_window(self) -> Generator[None]:
        """Scoped I/O window; an exception can never leave the window open."""
        self.enter_io()
        try:
            yield
        finally:
            self.exit_io()

    def check(self, *, now: float | None = None) -> bool:
        """One stall check; True exactly when this call fired the shutdown.

        Which budget applies is the whole M7-7(1) fix: a loop blocked in a declared
        transport call is measured against the (larger) I/O budget, a loop that simply
        stopped beating against the loop-liveness budget.
        """
        with self._lock:
            if self.fired or self._last_beat is None:
                return False
            moment = time.time() if now is None else now
            blocked = self._io_since
            since = self._last_beat if blocked is None else blocked
            budget = self._timeout if blocked is None else self._io_timeout
            if moment - since <= budget:
                return False
            self.fired = True
            silent_for = moment - since
            kind = (
                "loop stall: no heartbeat" if blocked is None else "transport stall: blocked in I/O"
            )
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        self._persist_path.write_text(
            json.dumps(self._snapshot(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self._on_stall(f"{kind} for {silent_for:.2f}s (state persisted)")
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


def announce_stall(
    reason: str,
    *,
    role: str,
    sink: Callable[[dict[str, Any]], None] | None,
    stream: TextIO,
) -> None:
    """Make a stall LOUD before a controlled exit (M7-7(3)).

    Input: the watchdog's reason, our role, the optional JSONL sink, the console stream.
    Output: none — the event is logged and the message is written AND FLUSHED. The flush
    is the point: the caller follows this with `os._exit`, which skips interpreter
    shutdown entirely, so an unflushed buffer dies with the process and the operator
    watching a live match sees an unexplained death (observed in the kill drill).
    """
    if sink is not None:
        sink({"event": "watchdog_stall", "sender": role, "payload": {"reason": reason}})
    stream.write(f"WATCHDOG [{role}]: {reason}\n")
    stream.flush()

"""Token-bucket rate limiter with a bounded FIFO wait queue (M6-5; PRD_gatekeeper §3).

Sliding-window requests-per-minute + a concurrency semaphore (the signed
`concurrent_requests` key the reference never enforces) + queue-never-crash
semantics: overflow and timeout raise `RateLimitError` for the caller to handle.
All limits arrive from config; the injectable clock keeps tests deterministic
and instant (the reference's own test trick, adopted wholesale).
"""

from __future__ import annotations

import threading
import time as _time
from collections import deque
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Protocol

WINDOW_SECONDS = 60.0  # a "requests per minute" window is a minute by definition


class Clock(Protocol):
    """The two clock calls the limiter makes — swappable for a fake in tests."""

    def time(self) -> float: ...

    def sleep(self, seconds: float) -> None: ...


class _RealClock:
    def time(self) -> float:
        return _time.time()

    def sleep(self, seconds: float) -> None:
        _time.sleep(seconds)


class RateLimitError(RuntimeError):
    """No slot available: queue full or wait timed out (caller queues or degrades)."""


@dataclass(frozen=True)
class QueueLimits:
    """`rate_limits.json` `queue` block: wait pacing + patience for a slot."""

    drain_interval_seconds: float
    timeout_seconds: float


class RateLimiter:
    """Sliding-window + concurrency limiter; `slot()` is the only doorway."""

    def __init__(
        self,
        *,
        requests_per_minute: int,
        concurrent_requests: int,
        queue: QueueLimits,
        max_depth: int,
        clock: Clock | None = None,
    ) -> None:
        self._rpm = requests_per_minute
        self._queue = queue
        self._max_depth = max_depth
        self._clock: Clock = clock if clock is not None else _RealClock()
        self._grants: deque[float] = deque()  # timestamps of recent window grants
        self._semaphore = threading.BoundedSemaphore(concurrent_requests)
        self._waiting = 0
        self._lock = threading.Lock()

    @property
    def queue_depth(self) -> int:
        """How many callers are currently queued waiting for a slot."""
        return self._waiting

    def _try_grant(self) -> bool:
        """One atomic attempt: window slot AND concurrency token, or neither."""
        with self._lock:
            now = self._clock.time()
            while self._grants and now - self._grants[0] >= WINDOW_SECONDS:
                self._grants.popleft()
            if len(self._grants) >= self._rpm:
                return False
            if not self._semaphore.acquire(blocking=False):
                return False
            self._grants.append(now)
            return True

    def _acquire(self) -> None:
        if self._try_grant():
            return
        with self._lock:
            if self._waiting >= self._max_depth:
                raise RateLimitError(f"Rate-limit queue full (max_depth={self._max_depth})")
            self._waiting += 1
        try:
            deadline = self._clock.time() + self._queue.timeout_seconds
            while self._clock.time() < deadline:
                self._clock.sleep(self._queue.drain_interval_seconds)
                if self._try_grant():
                    return
            raise RateLimitError(
                f"Timed out after {self._queue.timeout_seconds}s waiting for a rate slot"
            )
        finally:
            with self._lock:
                self._waiting -= 1

    @contextmanager
    def slot(self) -> Generator[None]:
        """Hold one granted slot for the duration of the external call."""
        self._acquire()
        try:
            yield
        finally:
            self._semaphore.release()

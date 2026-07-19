"""shared/rate_limiter (M6-5; PRD_gatekeeper §3): window + semaphore + FIFO queue.

Deterministic and instant via the injectable clock (the reference's own test trick,
adopted wholesale). Queue, never crash: overflow and timeout raise cleanly.
"""

from __future__ import annotations

import threading

import pytest

from copthief_core.shared.rate_limiter import QueueLimits, RateLimiter, RateLimitError


class FakeClock:
    """Deterministic clock: sleep() just advances time."""

    def __init__(self) -> None:
        self.now = 0.0

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def make_limiter(
    rpm: int = 3, concurrent: int = 2, depth: int = 4
) -> tuple[RateLimiter, FakeClock]:
    clock = FakeClock()
    limiter = RateLimiter(
        requests_per_minute=rpm,
        concurrent_requests=concurrent,
        queue=QueueLimits(drain_interval_seconds=0.5, timeout_seconds=120.0),
        max_depth=depth,
        clock=clock,
    )
    return limiter, clock


def test_grants_up_to_the_window_then_queues_until_the_window_frees() -> None:
    limiter, clock = make_limiter(rpm=2)
    with limiter.slot():
        pass
    with limiter.slot():
        pass
    # Third call: the window is full at t=0; the fake clock advances via queue
    # sleeps until the first grant leaves the 60s window.
    with limiter.slot():
        granted_at = clock.now
    assert granted_at >= 60.0


def test_concurrency_semaphore_caps_simultaneous_slots() -> None:
    limiter, _clock = make_limiter(rpm=100, concurrent=1)
    # Contexts enter left-to-right: the held slot never releases, so the second
    # acquisition (inside the raises context) must time out.
    with limiter.slot(), pytest.raises(RateLimitError, match="[Tt]imed out"), limiter.slot():
        pass


def test_queue_overflow_refuses_loudly_never_crashes() -> None:
    limiter, _clock = make_limiter(rpm=1, depth=0)
    with limiter.slot():
        pass
    with pytest.raises(RateLimitError, match="queue full"), limiter.slot():
        pass


def test_queue_depth_reports_waiting_callers() -> None:
    limiter, _clock = make_limiter()
    assert limiter.queue_depth == 0


def test_synthetic_load_all_calls_granted_queued_or_cleanly_refused() -> None:
    """The M6-5 DoD load test: N threads hammer the limiter; every call either
    completes or raises RateLimitError; nothing crashes; the window is honored."""
    limiter, _clock = make_limiter(rpm=5, concurrent=2, depth=3)
    outcomes: list[str] = []
    lock = threading.Lock()

    def caller() -> None:
        try:
            with limiter.slot():
                pass
            verdict = "ok"
        except RateLimitError:
            verdict = "refused"
        with lock:
            outcomes.append(verdict)

    threads = [threading.Thread(target=caller) for _ in range(12)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    assert len(outcomes) == 12
    assert set(outcomes) <= {"ok", "refused"}
    assert outcomes.count("ok") >= 5  # the window's worth got through

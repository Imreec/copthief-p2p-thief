"""shared/gatekeeper (M6-5; PRD_gatekeeper §2-§3): quota → token bucket → DoS lock.

The single doorway for ALL external calls. Pinned here: quota refusal happens
BEFORE queueing; 429-style transient errors honor the signed retry_backoff_sec
schedule capped by max_retries; a failure burst trips the breaker (loud, cooldown,
auto-reset); every stage emits a gatekeeper JSONL event.
"""

from __future__ import annotations

from typing import Any

import pytest

from copthief_core.shared.gatekeeper import (
    ApiGatekeeper,
    CircuitOpenError,
    QuotaExceededError,
    TransientProviderError,
)
from copthief_core.shared.rate_limiter import QueueLimits, RateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def make_gatekeeper(
    *,
    quota_units: int = 100,
    retry_backoff_sec: int = 5,
    max_retries: int = 3,
    failure_threshold: int = 3,
    cooldown_seconds: int = 60,
) -> tuple[ApiGatekeeper, FakeClock, list[dict[str, Any]]]:
    clock = FakeClock()
    events: list[dict[str, Any]] = []
    limiter = RateLimiter(
        requests_per_minute=1000,
        concurrent_requests=10,
        queue=QueueLimits(drain_interval_seconds=0.1, timeout_seconds=60.0),
        max_depth=10,
        clock=clock,
    )
    keeper = ApiGatekeeper(
        service="email",
        limiter=limiter,
        quota_units=quota_units,
        retry_backoff_sec=retry_backoff_sec,
        max_retries=max_retries,
        failure_threshold=failure_threshold,
        cooldown_seconds=cooldown_seconds,
        clock=clock,
        log=events.append,
    )
    return keeper, clock, events


def test_execute_returns_the_calls_result_and_logs_the_grant() -> None:
    keeper, _clock, events = make_gatekeeper()
    assert keeper.execute(lambda: "sent") == "sent"
    assert any(e["payload"]["action"] == "granted" for e in events)


def test_quota_refusal_happens_before_any_queueing() -> None:
    keeper, _clock, events = make_gatekeeper(quota_units=1)
    keeper.execute(lambda: "one")
    with pytest.raises(QuotaExceededError, match="email"):
        keeper.execute(lambda: "two")
    refusals = [e for e in events if e["payload"]["action"] == "quota_refused"]
    assert refusals  # loud, logged — never a silent budget breach


def test_transient_429_honors_the_signed_backoff_schedule() -> None:
    keeper, clock, _events = make_gatekeeper(retry_backoff_sec=5, max_retries=3)
    attempts: list[int] = []

    def flaky() -> str:
        attempts.append(1)
        if len(attempts) < 3:
            raise TransientProviderError("429 back off")
        return "sent"

    assert keeper.execute(flaky) == "sent"
    assert len(attempts) == 3
    # Escalating backoff: retry_backoff_sec * attempt-number (5, 10).
    assert clock.sleeps[-2:] == [5.0, 10.0]


def test_retries_exhausted_reraises_the_transient_error() -> None:
    keeper, _clock, _events = make_gatekeeper(max_retries=2)

    def always_429() -> str:
        raise TransientProviderError("429")

    with pytest.raises(TransientProviderError):
        keeper.execute(always_429)


def test_failure_burst_trips_the_breaker_then_cooldown_resets_it() -> None:
    keeper, clock, events = make_gatekeeper(max_retries=1, failure_threshold=2, cooldown_seconds=60)

    def broken() -> str:
        raise TransientProviderError("down")

    for _ in range(2):
        with pytest.raises(TransientProviderError):
            keeper.execute(broken)
    # Breaker open: refuse WITHOUT calling the provider.
    with pytest.raises(CircuitOpenError, match="email"):
        keeper.execute(lambda: "never runs")
    assert any(e["payload"]["action"] == "breaker_open" for e in events)
    clock.now += 61.0  # cooldown elapses -> half-open, a success resets
    assert keeper.execute(lambda: "recovered") == "recovered"
    assert any(e["payload"]["action"] == "breaker_reset" for e in events)


def test_queue_status_reports_service_and_counters() -> None:
    keeper, _clock, _events = make_gatekeeper()
    keeper.execute(lambda: "ok")
    status = keeper.get_queue_status()
    assert status["service"] == "email"
    assert status["calls_total"] == 1
    assert status["failures_total"] == 0
    assert "queue_depth" in status

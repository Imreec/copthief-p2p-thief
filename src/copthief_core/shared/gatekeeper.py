"""ApiGatekeeper — the single doorway for ALL external calls (M6-5; FR-9, PLAN §4).

Three stages, in order: (1) QUOTA — budget checked BEFORE queueing, a counted
series never silently breaches its ledger; (2) TOKEN BUCKET — the RateLimiter's
window/semaphore/queue; (3) DOS LOCK — transient provider pushback (429-style)
honors the signed `retry_backoff_sec` escalation capped by `max_retries`, and a
failure burst trips a cooldown breaker (loud, auto-reset on the next success).
Every stage emits a `gatekeeper` JSONL event through the optional LogFn.
"""

from __future__ import annotations

import time as _time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from copthief_core.shared.rate_limiter import Clock, RateLimiter

T = TypeVar("T")
LogFn = Callable[[dict[str, Any]], None]


@dataclass(frozen=True)
class BreakerLimits:
    """`rate_limits.json` `breaker` block: the DoS lock's trip point + cooldown."""

    failure_threshold: int
    cooldown_seconds: int


class _RealClock:
    def time(self) -> float:
        return _time.time()

    def sleep(self, seconds: float) -> None:
        _time.sleep(seconds)


class QuotaExceededError(RuntimeError):
    """The service's budget ledger is spent — refused before any queueing."""


class CircuitOpenError(RuntimeError):
    """The DoS breaker is open: the provider gets a cooldown, not more traffic."""


class TransientProviderError(RuntimeError):
    """A retryable provider failure (429 / transient) — adapters raise this."""


class ApiGatekeeper:
    """Centralized doorway with quota, rate control, retry, and a failure breaker."""

    def __init__(
        self,
        *,
        service: str,
        limiter: RateLimiter,
        quota_units: int,
        retry_backoff_sec: int,
        max_retries: int,
        failure_threshold: int,
        cooldown_seconds: int,
        clock: Clock | None = None,
        log: LogFn | None = None,
    ) -> None:
        self._service = service
        self._limiter = limiter
        self._quota_units = quota_units
        self._backoff = retry_backoff_sec
        self._max_retries = max_retries
        self._failure_threshold = failure_threshold
        self._cooldown = cooldown_seconds
        self._clock: Clock = clock if clock is not None else _RealClock()
        self._log = log
        self._spent = 0
        self._consecutive_failures = 0
        self._open_until: float | None = None
        self._calls_total = 0
        self._failures_total = 0

    def _emit(self, action: str, **detail: Any) -> None:  # noqa: ANN401 - event payload
        if self._log is not None:
            payload = {"service": self._service, "action": action, **detail}
            self._log({"event": "gatekeeper", "payload": payload})

    def _gate(self) -> None:
        """Stages 1 + 3a: quota ledger, then the breaker — both BEFORE queueing."""
        if self._spent >= self._quota_units:
            self._emit("quota_refused", spent=self._spent, quota=self._quota_units)
            raise QuotaExceededError(
                f"{self._service}: quota spent ({self._spent}/{self._quota_units})"
            )
        if self._open_until is not None:
            if self._clock.time() < self._open_until:
                self._emit("breaker_refused", open_until=self._open_until)
                raise CircuitOpenError(f"{self._service}: breaker open (cooldown)")
            self._emit("breaker_half_open")  # cooldown elapsed: allow one probe

    def execute(self, api_call: Callable[..., T], *args: Any, **kwargs: Any) -> T:  # noqa: ANN401
        """Run one external call under quota + rate control + retry + breaker."""
        self._gate()
        self._spent += 1
        last_error: TransientProviderError | None = None
        for attempt in range(1, self._max_retries + 1):
            with self._limiter.slot():
                self._calls_total += 1
                try:
                    result = api_call(*args, **kwargs)
                except TransientProviderError as error:
                    last_error = error
                    self._note_failure(attempt, error)
                else:
                    self._consecutive_failures = 0
                    if self._open_until is not None:
                        self._open_until = None
                        self._emit("breaker_reset")
                    self._emit("granted", attempt=attempt)
                    return result
            if attempt < self._max_retries:
                # Signed escalation: retry_backoff_sec × attempt number (429 honored).
                self._emit("retry", attempt=attempt, backoff=self._backoff * attempt)
                self._clock.sleep(float(self._backoff * attempt))
        assert last_error is not None
        raise last_error

    def _note_failure(self, attempt: int, error: TransientProviderError) -> None:
        self._failures_total += 1
        self._consecutive_failures += 1
        self._emit("provider_failure", attempt=attempt, error=str(error))
        if self._consecutive_failures >= self._failure_threshold and self._open_until is None:
            self._open_until = self._clock.time() + self._cooldown
            self._emit("breaker_open", cooldown=self._cooldown)

    def get_queue_status(self) -> dict[str, Any]:
        """Observability snapshot: queue depth + call/failure counters."""
        return {
            "service": self._service,
            "queue_depth": self._limiter.queue_depth,
            "calls_total": self._calls_total,
            "failures_total": self._failures_total,
            "quota_spent": self._spent,
        }

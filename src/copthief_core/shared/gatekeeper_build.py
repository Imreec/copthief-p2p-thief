"""Gatekeeper assembly from the loaded v1.01 RateLimits (M6-5), split from
shared/gatekeeper (150-line rule). The seam the M6-4 email sender consumes."""

from __future__ import annotations

from copthief_core.shared.config_model import RateLimits
from copthief_core.shared.gatekeeper import ApiGatekeeper, LogFn
from copthief_core.shared.rate_limiter import Clock, QueueLimits, RateLimiter


def build_gatekeeper(
    service: str,
    limits: RateLimits,
    *,
    quota_units: int,
    clock: Clock | None = None,
    log: LogFn | None = None,
) -> ApiGatekeeper:
    """One service's gatekeeper from the loaded limits, applying any
    (loader-validated, tighten-only) per-service overrides.

    Input: service name ("email"/"llm") + typed RateLimits + the service's quota
    budget (email: `limits.email_daily_cap`; llm: the signed token budget).
    Output: a ready ApiGatekeeper wrapping a fresh RateLimiter.
    """

    def effective(key: str) -> int:
        return int(limits.services.get(service, {}).get(key, getattr(limits, key)))

    limiter = RateLimiter(
        requests_per_minute=effective("requests_per_minute"),
        concurrent_requests=effective("concurrent_requests"),
        queue=QueueLimits(
            drain_interval_seconds=limits.queue.drain_interval_seconds,
            timeout_seconds=limits.queue.timeout_seconds,
        ),
        max_depth=effective("queue_depth"),
        clock=clock,
    )
    return ApiGatekeeper(
        service=service,
        limiter=limiter,
        quota_units=quota_units,
        retry_backoff_sec=effective("retry_backoff_sec"),
        max_retries=effective("max_retries"),
        failure_threshold=limits.breaker.failure_threshold,
        cooldown_seconds=limits.breaker.cooldown_seconds,
        clock=clock,
        log=log,
    )

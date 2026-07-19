"""rate_limits.json v1.01 loading (M6-5), split from shared/config (150-line rule).

FR-9 precedence, unchanged and extended: every shared flat key must meet or exceed
the signed `rate_limiter_gatekeeper` minimums, and per-service overrides may only
TIGHTEN — each stays within [signed minimum, global operational value]. A violation
refuses the load loudly (the gatekeeper never runs on illegal limits).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from copthief_core.shared.config_model import GatekeeperParams, RateLimits
from copthief_core.shared.gatekeeper import BreakerLimits
from copthief_core.shared.private_config import ConfigError, validated_version
from copthief_core.shared.rate_limiter import QueueLimits

_SHARED_KEYS = (
    "requests_per_minute",
    "concurrent_requests",
    "retry_backoff_sec",
    "max_retries",
    "queue_depth",
)


def _check_overrides(limits: RateLimits, signed: GatekeeperParams, source: str) -> None:
    """Tighten-only band per approved PRD_gatekeeper §6: [signed minimum, global]."""
    for service, overrides in limits.services.items():
        for key, value in overrides.items():
            if key not in _SHARED_KEYS:
                raise ConfigError(f"{source}: unknown service override key {service}.{key}")
            if value < getattr(signed, key):
                raise ConfigError(
                    f"{source}: {service}.{key}={value} is below the signed "
                    f"minimum {getattr(signed, key)}"
                )
            if value > getattr(limits, key):
                raise ConfigError(
                    f"{source}: {service}.{key}={value} loosens the global "
                    f"{getattr(limits, key)} — service overrides may only tighten"
                )


def load_rate_limits(path: Path, gatekeeper: GatekeeperParams) -> RateLimits:
    """Load the operational limits and assert the signed-minimums precedence (FR-9).

    Input: rate_limits.json path + the signed gatekeeper block; Output: typed
    RateLimits (v1.01: queue/breaker/email blocks + validated service overrides);
    Raises: ConfigError naming every breach.
    """
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    limits = RateLimits(
        version=validated_version(raw, path.name),
        requests_per_minute=int(raw["requests_per_minute"]),
        concurrent_requests=int(raw["concurrent_requests"]),
        retry_backoff_sec=int(raw["retry_backoff_sec"]),
        max_retries=int(raw["max_retries"]),
        queue_depth=int(raw["queue_depth"]),
        queue=QueueLimits(
            drain_interval_seconds=float(raw["queue"]["drain_interval_seconds"]),
            timeout_seconds=float(raw["queue"]["timeout_seconds"]),
        ),
        breaker=BreakerLimits(
            failure_threshold=int(raw["breaker"]["failure_threshold"]),
            cooldown_seconds=int(raw["breaker"]["cooldown_seconds"]),
        ),
        email_daily_cap=int(raw["email"]["daily_cap"]),
        services={
            str(service): {str(k): int(v) for k, v in overrides.items()}
            for service, overrides in raw.get("services", {}).items()
        },
    )
    breaches = [key for key in _SHARED_KEYS if getattr(limits, key) < getattr(gatekeeper, key)]
    if breaches:
        raise ConfigError(
            f"{path.name}: below the signed gatekeeper minimums: {', '.join(breaches)}"
        )
    _check_overrides(limits, gatekeeper, path.name)
    return limits

"""rate_limits.json v1.01 (M6-5; PRD_gatekeeper §6): queue/breaker/email blocks +
per-service overrides that may only TIGHTEN within [signed minimum, global value]."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from copthief_core.shared.config import ConfigError, load_rate_limits
from copthief_core.shared.config_model import GatekeeperParams

SIGNED = GatekeeperParams(
    requests_per_minute=10,
    concurrent_requests=2,
    retry_backoff_sec=5,
    max_retries=3,
    queue_depth=50,
)


def base_raw() -> dict[str, Any]:
    return {
        "version": "1.01",
        "requests_per_minute": 30,
        "concurrent_requests": 2,
        "retry_backoff_sec": 5,
        "max_retries": 3,
        "queue_depth": 100,
        "queue": {"drain_interval_seconds": 0.5, "timeout_seconds": 30},
        "breaker": {"failure_threshold": 5, "cooldown_seconds": 60},
        "email": {"daily_cap": 10},
        "services": {},
    }


def write(tmp_path: Path, raw: dict[str, Any]) -> Path:
    path = tmp_path / "rate_limits.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    return path


def test_shipped_rate_limits_carry_the_v101_blocks() -> None:
    limits = load_rate_limits(Path("config") / "rate_limits.json", SIGNED)
    assert limits.queue.drain_interval_seconds > 0
    assert limits.queue.timeout_seconds > 0
    assert limits.breaker.failure_threshold >= 1
    assert limits.breaker.cooldown_seconds >= 1
    assert limits.email_daily_cap >= 1


def test_v101_file_parses_queue_breaker_and_email(tmp_path: Path) -> None:
    limits = load_rate_limits(write(tmp_path, base_raw()), SIGNED)
    assert limits.queue.timeout_seconds == 30
    assert limits.breaker.failure_threshold == 5
    assert limits.email_daily_cap == 10
    assert limits.services == {}


def test_service_override_inside_the_band_is_accepted(tmp_path: Path) -> None:
    raw = base_raw()
    raw["services"] = {"email": {"requests_per_minute": 15}}
    limits = load_rate_limits(write(tmp_path, raw), SIGNED)
    assert limits.services["email"]["requests_per_minute"] == 15


def test_service_override_below_the_signed_minimum_is_refused(tmp_path: Path) -> None:
    raw = base_raw()
    raw["services"] = {"email": {"requests_per_minute": 5}}  # signed minimum is 10
    with pytest.raises(ConfigError, match="signed"):
        load_rate_limits(write(tmp_path, raw), SIGNED)


def test_service_override_above_the_global_value_is_refused(tmp_path: Path) -> None:
    raw = base_raw()
    raw["services"] = {"email": {"requests_per_minute": 60}}  # global is 30: loosen = refuse
    with pytest.raises(ConfigError, match="tighten"):
        load_rate_limits(write(tmp_path, raw), SIGNED)


def test_build_gatekeeper_wires_the_tightened_override_and_the_email_quota(
    tmp_path: Path,
) -> None:
    from copthief_core.shared.gatekeeper_build import build_gatekeeper

    raw = base_raw()
    raw["services"] = {"email": {"requests_per_minute": 15}}
    limits = load_rate_limits(write(tmp_path, raw), SIGNED)
    keeper = build_gatekeeper("email", limits, quota_units=limits.email_daily_cap)
    assert keeper.execute(lambda: "ok") == "ok"
    status = keeper.get_queue_status()
    assert status["service"] == "email"
    assert status["quota_spent"] == 1
    # The override reached the limiter (white-box pin: the wiring, not the math).
    assert keeper._limiter._rpm == 15  # noqa: SLF001


def test_flat_keys_still_honor_the_signed_minimums(tmp_path: Path) -> None:
    raw = base_raw()
    raw["requests_per_minute"] = 5  # below the signed minimum 10
    with pytest.raises(ConfigError, match="minimum"):
        load_rate_limits(write(tmp_path, raw), SIGNED)

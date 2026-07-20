"""Shared fixtures for the M7-6 email-sender suites (split per the 150-line rule).

Imported by `test_email_sender.py` (the acting paths) and `test_email_refusals.py`
(the paths that must touch no transport) — one definition, two suites (DRY, §4.2).
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from copthief_core.infra.email_sender import EmailSender
from copthief_core.report.emit import artifact_bytes
from copthief_core.shared.config_model import EmailSettings
from copthief_core.shared.gatekeeper import ApiGatekeeper
from copthief_core.shared.rate_limiter import QueueLimits, RateLimiter

UID = "uid-1234"
LECTURER = ("lecturer@example.test",)
FRIENDLY = ("team@example.test", "peer.team@example.test")


class FakeTransport:
    """Records draft/send calls; anything reaching it without a recipient is the bug."""

    def __init__(self) -> None:
        self.drafts: list[dict[str, Any]] = []
        self.sends: list[dict[str, Any]] = []

    def create_draft(
        self, *, to: Sequence[str], subject: str, body: str, attachment_name: str | None = None
    ) -> None:
        self.drafts.append(
            {"to": tuple(to), "subject": subject, "body": body, "attachment": attachment_name}
        )

    def send(
        self, *, to: Sequence[str], subject: str, body: str, attachment_name: str | None = None
    ) -> None:
        self.sends.append(
            {"to": tuple(to), "subject": subject, "body": body, "attachment": attachment_name}
        )


def result_file(tmp_path: Path, *, winner: str | None = "team-a") -> Path:
    """A minimal result artifact written with the real serializer (byte-faithful)."""
    data: dict[str, Any] = {"game_uid": UID, "final_result": {"winner_group": winner}}
    path = tmp_path / "result_x.json"
    path.write_bytes(artifact_bytes(data))
    return path


def settings(
    *, enabled: bool = True, mode: str = "send", recipient: tuple[str, ...] = LECTURER
) -> EmailSettings:
    return EmailSettings(
        enabled=enabled,
        mode=mode,
        recipient=recipient,
        sender="team@example.test",
        token_path="token.json",
    )


def keeper(quota: int = 5) -> ApiGatekeeper:
    limiter = RateLimiter(
        requests_per_minute=100,
        concurrent_requests=2,
        queue=QueueLimits(drain_interval_seconds=0.01, timeout_seconds=1.0),
        max_depth=5,
    )
    return ApiGatekeeper(
        service="email",
        limiter=limiter,
        quota_units=quota,
        retry_backoff_sec=1,
        max_retries=1,
        failure_threshold=3,
        cooldown_seconds=10,
    )


def make_sender(
    *,
    enabled: bool = True,
    mode: str = "send",
    recipient: tuple[str, ...] = LECTURER,
    quota: int = 5,
) -> tuple[EmailSender, FakeTransport]:
    transport = FakeTransport()
    sender = EmailSender(
        settings=settings(enabled=enabled, mode=mode, recipient=recipient),
        gatekeeper=keeper(quota),
        transport=transport,
    )
    return sender, transport

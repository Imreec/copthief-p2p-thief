"""M6-4 email sender (PRD_reporting §5): interlocked, gatekept, byte-faithful.

Pinned here: the emailed body IS the result artifact's file bytes (canonical =
emailed, PLAN §4); the draft path provably constructs no send call; every
invocation passes through the email gatekeeper (quota enforced); refusals touch
no transport at all.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from copthief_core.infra.email_sender import EmailSender
from copthief_core.report.emit import artifact_bytes
from copthief_core.shared.config_model import EmailSettings
from copthief_core.shared.gatekeeper import ApiGatekeeper, QuotaExceededError
from copthief_core.shared.rate_limiter import QueueLimits, RateLimiter

UID = "uid-1234"


class FakeTransport:
    """Records draft/send calls; a send in draft mode is the failure we hunt."""

    def __init__(self) -> None:
        self.drafts: list[dict[str, str]] = []
        self.sends: list[dict[str, str]] = []

    def create_draft(self, *, to: str, subject: str, body: str) -> None:
        self.drafts.append({"to": to, "subject": subject, "body": body})

    def send(self, *, to: str, subject: str, body: str) -> None:
        self.sends.append({"to": to, "subject": subject, "body": body})


def result_file(tmp_path: Path) -> Path:
    data = {
        "game_uid": UID,
        "final_result": {"winner_group": "team-a"},
    }
    path = tmp_path / "result_x.json"
    path.write_bytes(artifact_bytes(data))
    return path


def settings(*, enabled: bool = True, mode: str = "draft") -> EmailSettings:
    return EmailSettings(
        enabled=enabled,
        mode=mode,
        recipient="lecturer@example.test",
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
    *, enabled: bool = True, mode: str = "draft", quota: int = 5
) -> tuple[EmailSender, FakeTransport]:
    transport = FakeTransport()
    sender = EmailSender(
        settings=settings(enabled=enabled, mode=mode), gatekeeper=keeper(quota), transport=transport
    )
    return sender, transport


def test_draft_mode_creates_the_draft_and_provably_never_sends(tmp_path: Path) -> None:
    sender, transport = make_sender(mode="draft")
    outcome = sender.send_report(result_path=result_file(tmp_path), role="police", armed=UID)
    assert outcome["action"] == "draft"
    assert len(transport.drafts) == 1
    assert transport.sends == []  # the iron pin: draft mode cannot send, even armed


def test_emailed_body_bytes_are_the_artifact_file_bytes(tmp_path: Path) -> None:
    sender, transport = make_sender(mode="draft")
    path = result_file(tmp_path)
    sender.send_report(result_path=path, role="police")
    assert transport.drafts[0]["body"].encode("utf-8") == path.read_bytes()
    assert transport.drafts[0]["to"] == "lecturer@example.test"
    assert "winner team-a" in transport.drafts[0]["subject"]
    assert "(reported by police)" in transport.drafts[0]["subject"]


def test_armed_send_matches_the_uid_and_sends_once(tmp_path: Path) -> None:
    sender, transport = make_sender(mode="send")
    outcome = sender.send_report(result_path=result_file(tmp_path), role="police", armed=UID)
    assert outcome["action"] == "send"
    assert len(transport.sends) == 1
    assert transport.drafts == []


@pytest.mark.parametrize(
    ("enabled", "mode", "armed"),
    [
        (False, "draft", None),  # disabled
        (True, "send", None),  # unarmed
        (True, "send", "wrong"),  # mismatched retype
    ],
)
def test_refusals_touch_no_transport_and_name_their_reason(
    tmp_path: Path, enabled: bool, mode: str, armed: str | None
) -> None:
    sender, transport = make_sender(enabled=enabled, mode=mode)
    outcome = sender.send_report(result_path=result_file(tmp_path), role="police", armed=armed)
    assert outcome["action"] == "refuse"
    assert outcome["reason"]
    assert transport.drafts == []
    assert transport.sends == []


def test_the_email_quota_is_enforced_through_the_gatekeeper(tmp_path: Path) -> None:
    sender, _transport = make_sender(mode="draft", quota=1)
    path = result_file(tmp_path)
    sender.send_report(result_path=path, role="police")
    with pytest.raises(QuotaExceededError):
        sender.send_report(result_path=path, role="police")


def test_series_tie_subject_degrades_to_tie(tmp_path: Path) -> None:
    data: dict[str, Any] = {"game_uid": UID, "final_result": {"winner_group": None}}
    path = tmp_path / "result_tie.json"
    path.write_bytes(artifact_bytes(data))
    sender, transport = make_sender(mode="draft")
    sender.send_report(result_path=path, role="thief")
    assert "winner tie" in transport.drafts[0]["subject"]


def test_missing_result_file_refuses_loudly(tmp_path: Path) -> None:
    sender, transport = make_sender(mode="draft")
    with pytest.raises(FileNotFoundError):
        sender.send_report(result_path=tmp_path / "absent.json", role="police")
    assert transport.drafts == []

"""M6-4 Gmail transport (App A; HW6 salvage, D1=A): pure MIME + the compose scope.

Only `build_raw` runs keyless (pure MIME → base64url); the live draft/send paths
import the Google SDK lazily and are exercised by the operator, never CI.
"""

from __future__ import annotations

import base64
from email import message_from_bytes

from copthief_core.infra.gmail import SCOPES, GmailTransport


def test_scope_is_compose_only_per_the_d1_ruling() -> None:
    """gmail.compose: create/send drafts and messages, NO mailbox read — the least
    privilege that supports the draft rail (PR #43 D1=A; CLAUDE.md §4 amended)."""
    assert SCOPES == ["https://www.googleapis.com/auth/gmail.compose"]


def test_build_raw_round_trips_headers_and_utf8_body() -> None:
    transport = GmailTransport(sender="team@example.test")
    raw = transport.build_raw(
        to="lecturer@example.test",
        subject="Police-Thief series result: winner team-a (reported by police)",
        body='{\n  "תוצאה": "לכידה"\n}',
    )
    message = message_from_bytes(base64.urlsafe_b64decode(raw))
    assert message["To"] == "lecturer@example.test"
    assert message["From"] == "team@example.test"
    assert "winner team-a" in str(message["Subject"])
    payload = message.get_payload(decode=True)
    assert isinstance(payload, bytes)
    assert payload.decode("utf-8") == '{\n  "תוצאה": "לכידה"\n}'

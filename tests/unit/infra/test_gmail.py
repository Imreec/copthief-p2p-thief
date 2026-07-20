"""M7-6 Gmail transport (App A; ADR-0008): send-only scope, multi-recipient, attachment.

Only `build_raw` runs keyless (pure MIME → base64url); the live send path imports the
Google SDK lazily and is exercised by the operator, never CI.
"""

from __future__ import annotations

import base64
import json
from email import message_from_bytes

from copthief_core.infra.gmail import SCOPES, GmailTransport

ARTIFACT = '{\n  "winner_group": "imreeyal",\n  "תוצאה": "לכידה"\n}'


def test_scope_is_send_only_per_app_e_rule_30() -> None:
    """App E rule 30 + App A §1.3/§3 mandate send-only (sanction: security deviation →
    code disqualification). ADR-0008 dropped draft as a posture precisely so this scope
    could be satisfied literally rather than by argument — `gmail.send` is NOT among
    `users.drafts.create`'s scopes, verified against Google's API reference."""
    assert SCOPES == ["https://www.googleapis.com/auth/gmail.send"]


def test_build_raw_round_trips_headers_and_utf8_body() -> None:
    transport = GmailTransport(sender="team@example.test")
    raw = transport.build_raw(
        to=("lecturer@example.test",),
        subject="Police-Thief series result: winner team-a (reported by police)",
        body=ARTIFACT,
    )
    message = message_from_bytes(base64.urlsafe_b64decode(raw))
    assert message["To"] == "lecturer@example.test"
    assert message["From"] == "team@example.test"
    assert "winner team-a" in str(message["Subject"])
    body = next(p for p in message.walk() if p.get_content_type() == "text/plain")
    payload = body.get_payload(decode=True)
    assert isinstance(payload, bytes)
    assert payload.decode("utf-8") == ARTIFACT


def test_multiple_recipients_join_into_one_to_header() -> None:
    """The friendly report exchange addresses us AND the opponent team. Recipients are
    RFC-822 headers, so send-only scope does not constrain their count (verified against
    the API reference before ADR-0008 relied on it)."""
    transport = GmailTransport(sender="team@example.test")
    raw = transport.build_raw(
        to=("team@example.test", "peer.team@example.test"),
        subject="s",
        body=ARTIFACT,
    )
    message = message_from_bytes(base64.urlsafe_b64decode(raw))
    assert message["To"] == "team@example.test, peer.team@example.test"


def test_the_artifact_is_attached_as_a_json_file_per_rule_34() -> None:
    """App E rule 34: the report goes as an ATTACHED JSON file (sanction: a non-JSON
    report is refused → score zero). The body keeps the same bytes (reference-mirrored),
    so both readings of the rule are satisfied at once."""
    transport = GmailTransport(sender="team@example.test")
    raw = transport.build_raw(
        to=("lecturer@example.test",),
        subject="s",
        body=ARTIFACT,
        attachment_name="result_imreeyal-vs-peer.json",
    )
    message = message_from_bytes(base64.urlsafe_b64decode(raw))
    attachment = next(
        part for part in message.walk() if part.get_filename() == "result_imreeyal-vs-peer.json"
    )
    assert attachment.get_content_type() == "application/json"
    payload = attachment.get_payload(decode=True)
    assert isinstance(payload, bytes)
    # Byte-identical to the body, which is byte-identical to the artifact on disk.
    assert payload.decode("utf-8") == ARTIFACT
    assert json.loads(payload.decode("utf-8"))["winner_group"] == "imreeyal"

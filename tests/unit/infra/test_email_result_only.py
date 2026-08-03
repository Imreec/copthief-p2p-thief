"""M7-40: the series email is result-only again (Round 29, supersedes M7-37's set).

The attachment policy's full history, because this file is where it flip-flopped:
M7-37 read Moodle item 4 ("the agent sends the 4 JSON templates") as attach-everything
and shipped the 14-file superset, agreed with the opponent team. Round 29 settled it
the other way on three legs: the course chatbot's direct ruling (result-only in the
mail; logs/configs referenced, not embedded), the reference's own code (`emit_series`
returns ONLY the result "for emailing"; its sender puts it in the BODY), and pair
symmetry — the opponent team flipped first and pushed, and rule 35 punishes one-of-each
harder than either convention. The four template types stay VISIBLE IN THE REPOS (the
agreed exit criterion); they just don't ride the mail. Result stays body + the single
named attachment (book §9.3.3 + rule 34, the pre-M7-37 shape exactly). Both readings
of Moodle item 4 remain documented rather than adjudicated — the definitive closer is
a forum answer from the lecturer, not either team's parser.
"""

from __future__ import annotations

import base64
from email import message_from_bytes
from pathlib import Path

from email_fixtures import FRIENDLY, make_sender, result_file

from copthief_core.infra.gmail import GmailTransport
from copthief_core.report.emit import artifact_bytes

GID = "team-a-vs-team-b"


def _artifact_set(tmp_path: Path) -> Path:
    """A result whose FULL four-template sibling set sits beside it on disk."""
    result = tmp_path / f"result_{GID}.json"
    result.write_bytes(artifact_bytes({"game_uid": "uid-1234", "game_id": GID}))
    for name in (
        f"declaration_{GID}.json",
        f"config_{GID}_g01.json",
        f"config_{GID}_g02.json",
        f"log_{GID}_g01.json",
        f"log_{GID}_g02.json",
        f"report_{GID}_g01.json",
    ):
        (tmp_path / name).write_bytes(artifact_bytes({"file": name}))
    return result


def test_the_series_email_attaches_the_result_alone(tmp_path: Path) -> None:
    """The Round-29 pin: even with the complete sibling set present on disk, nothing
    but the result rides — the flip must not depend on the siblings being absent."""
    result = _artifact_set(tmp_path)
    sender, transport = make_sender(recipient=FRIENDLY)
    outcome = sender.send_report(result_path=result, role="police")
    assert outcome["action"] == "send"
    sent = transport.sends[0]
    assert sent["attachment"] == f"result_{GID}.json"
    assert sent["extra"] == []  # the M7-37 superset never rides again
    assert outcome["attachments"] == [f"result_{GID}.json"]


def test_a_bare_result_reports_identically(tmp_path: Path) -> None:
    # Siblings present or absent, the mail is the same shape — one code path.
    sender, transport = make_sender(recipient=FRIENDLY)
    outcome = sender.send_report(result_path=result_file(tmp_path), role="police")
    assert outcome["action"] == "send"
    assert transport.sends[0]["extra"] == []
    assert outcome["attachments"] == ["result_x.json"]


def test_transport_extra_attachment_capability_is_intact() -> None:
    """The TRANSPORT keeps the multi-attachment capability (generic, tested here so
    the policy above stays a policy — flipping it back is a one-line change, not a
    transport rebuild)."""
    transport = GmailTransport(sender="team@example.test")
    raw = transport.build_raw(
        to=["a@example.test"],
        subject="s",
        body='{"x": 1}',
        attachment_name="result_x.json",
        extra_attachments=[("declaration_x.json", b'{"d": 2}')],
    )
    message = message_from_bytes(base64.urlsafe_b64decode(raw))
    parts = {p.get_filename(): p for p in message.walk() if p.get_filename()}
    assert set(parts) == {"result_x.json", "declaration_x.json"}
    assert parts["declaration_x.json"].get_payload(decode=True) == b'{"d": 2}'
    body = next(
        p for p in message.walk() if p.get_content_type() == "text/plain" and not p.get_filename()
    )
    assert body.get_payload(decode=True) == b'{"x": 1}'  # rule 34: body untouched

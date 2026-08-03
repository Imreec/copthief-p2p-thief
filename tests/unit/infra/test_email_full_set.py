"""M7-37: the series email carries the full four-template evidence set (Moodle item 4).

The grader's own assignment instruction (verified screenshot, 2026-08-03): the agent
sends the lecturer the four attached JSON templates at game end, signed and agreed by
both teams. Superset resolution agreed with the opponent team: the ONE series email
attaches every instance of all four template types — declaration (1) + config g01..gNN
+ log g01..gNN + result (1) — while the result stays the body and the named attachment
(book §9.3.3 + rule 34 untouched). The per-game Hebrew `report_*.json` files are NOT
one of the four templates and never ride. Attachment presence is REPORTED, never
load-bearing: a missing sibling must not cost the report itself (rule 35 zeroes both
teams on a missing report; a thin mail is recoverable, an unsent one is not).
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
    """A result + its sibling artifact set for GID, plus one file that must NOT ride."""
    result = tmp_path / f"result_{GID}.json"
    result.write_bytes(artifact_bytes({"game_uid": "uid-1234", "game_id": GID}))
    for name in (
        f"declaration_{GID}.json",
        f"config_{GID}_g01.json",
        f"config_{GID}_g02.json",
        f"log_{GID}_g01.json",
        f"log_{GID}_g02.json",
        f"report_{GID}_g01.json",  # Hebrew per-game report: not one of the four
    ):
        (tmp_path / name).write_bytes(artifact_bytes({"file": name}))
    return result


def test_build_raw_carries_every_extra_file_and_keeps_the_body() -> None:
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


def test_the_series_email_attaches_the_whole_template_set(tmp_path: Path) -> None:
    result = _artifact_set(tmp_path)
    sender, transport = make_sender(recipient=FRIENDLY)
    outcome = sender.send_report(result_path=result, role="police")
    assert outcome["action"] == "send"
    sent = transport.sends[0]
    assert sent["attachment"] == f"result_{GID}.json"
    extra_names = [name for name, _payload in sent["extra"]]
    assert extra_names == [
        f"declaration_{GID}.json",
        f"config_{GID}_g01.json",
        f"config_{GID}_g02.json",
        f"log_{GID}_g01.json",
        f"log_{GID}_g02.json",
    ]  # ordered, report_* excluded
    assert outcome["attachments"] == [*extra_names, f"result_{GID}.json"]


def test_a_result_without_siblings_still_reports_alone(tmp_path: Path) -> None:
    # Reporting beats completeness: rule 35 punishes the missing REPORT; a thin mail
    # is visible in the outcome and recoverable by hand.
    sender, transport = make_sender(recipient=FRIENDLY)
    outcome = sender.send_report(result_path=result_file(tmp_path), role="police")
    assert outcome["action"] == "send"
    assert transport.sends[0]["extra"] == []
    assert outcome["attachments"] == ["result_x.json"]

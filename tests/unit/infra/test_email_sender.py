"""M7-6 email sender — the ACTING paths (ADR-0008): automatic, byte-faithful, attached.

Pinned here: a configured recipient sends with no human step (App E rule 32); the emailed
body IS the result artifact's file bytes (canonical = emailed, PLAN §4); the same bytes
ride as an attached JSON file (rule 34); a friendly addresses us AND the opponent.
Refusal paths live in `test_email_refusals.py`; fixtures in `email_fixtures.py`.
"""

from __future__ import annotations

from pathlib import Path

from email_fixtures import FRIENDLY, LECTURER, make_sender, result_file


def test_a_configured_recipient_sends_automatically_with_no_human_step(tmp_path: Path) -> None:
    """App E rule 32: reporting is automatic. No arming argument exists to forget —
    and rule 35 would have zeroed the OPPONENT's game too if we had kept one."""
    sender, transport = make_sender()
    outcome = sender.send_report(result_path=result_file(tmp_path), role="police")
    assert outcome["action"] == "send"
    assert len(transport.sends) == 1
    assert transport.drafts == []
    assert outcome["recipients"] == list(LECTURER)  # every act records where it went


def test_emailed_body_bytes_are_the_artifact_file_bytes(tmp_path: Path) -> None:
    sender, transport = make_sender()
    path = result_file(tmp_path)
    sender.send_report(result_path=path, role="police")
    assert transport.sends[0]["body"].encode("utf-8") == path.read_bytes()
    assert transport.sends[0]["to"] == LECTURER
    assert "winner team-a" in transport.sends[0]["subject"]
    assert "(reported by police)" in transport.sends[0]["subject"]


def test_the_artifact_rides_as_an_attachment_named_after_the_file(tmp_path: Path) -> None:
    """App E rule 34 wants an attached JSON file (sanction: non-JSON refused → score
    zero); the filename is the artifact's own, so the lecturer's tooling sees the
    same name that appears in the submitted artifacts."""
    sender, transport = make_sender()
    path = result_file(tmp_path)
    sender.send_report(result_path=path, role="police")
    assert transport.sends[0]["attachment"] == path.name


def test_the_friendly_exchange_addresses_us_and_the_opponent(tmp_path: Path) -> None:
    """Friendlies prove the format on both sides BEFORE the lecturer is ever addressed —
    rule 35 punishes contradictory reports as harshly as missing ones."""
    sender, transport = make_sender(recipient=FRIENDLY)
    outcome = sender.send_report(result_path=result_file(tmp_path), role="police")
    assert transport.sends[0]["to"] == FRIENDLY
    assert outcome["recipients"] == list(FRIENDLY)


def test_draft_mode_still_drafts_for_a_compose_scoped_token(tmp_path: Path) -> None:
    """Retained, not shipped: the live token is send-only, so this path is unreachable
    in production — but the code stays honest about what it does."""
    sender, transport = make_sender(mode="draft")
    outcome = sender.send_report(result_path=result_file(tmp_path), role="police")
    assert outcome["action"] == "draft"
    assert len(transport.drafts) == 1
    assert transport.sends == []


def test_series_tie_subject_degrades_to_tie(tmp_path: Path) -> None:
    sender, transport = make_sender()
    sender.send_report(result_path=result_file(tmp_path, winner=None), role="thief")
    assert "winner tie" in transport.sends[0]["subject"]

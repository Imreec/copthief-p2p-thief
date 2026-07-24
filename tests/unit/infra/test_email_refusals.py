"""M7-6 email sender — the paths that must touch NO transport (ADR-0008).

With the per-send arming retype gone, the recipient is the authorization: a run with
none configured must be incapable of reaching Gmail, and the gatekeeper (App E rule 28)
is now the only thing standing between a runaway loop and the lecturer's inbox — the
book's own answer to the flood scenario it raises in §9.3.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from email_fixtures import LECTURER, LECTURER_ADDRESS, make_sender, result_file

from copthief_core.shared.gatekeeper import QuotaExceededError


@pytest.mark.parametrize(
    ("enabled", "mode", "recipient"),
    [
        (False, "send", LECTURER),  # disabled
        (True, "send", ()),  # NO recipient = no authorization
        (True, "send", ("",)),  # a blank address is not an address
        (True, "draft", ()),  # draft is no exemption
        (True, "yolo", LECTURER),  # unknown mode
    ],
)
def test_refusals_touch_no_transport_and_name_their_reason(
    tmp_path: Path, enabled: bool, mode: str, recipient: tuple[str, ...]
) -> None:
    sender, transport = make_sender(enabled=enabled, mode=mode, recipient=recipient)
    outcome = sender.send_report(result_path=result_file(tmp_path), role="police")
    assert outcome["action"] == "refuse"
    assert outcome["reason"]  # loud and specific — never a bare False
    assert transport.drafts == []
    assert transport.sends == []


def test_the_email_quota_is_enforced_through_the_gatekeeper(tmp_path: Path) -> None:
    """Runaway protection is the gatekeeper (rule 28), not human review — this is the
    guard that replaced the arming step, so it is load-bearing now."""
    sender, _transport = make_sender(quota=1)
    path = result_file(tmp_path)
    sender.send_report(result_path=path, role="police")
    with pytest.raises(QuotaExceededError):
        sender.send_report(result_path=path, role="police")


def test_the_lecturer_is_unreachable_from_an_uncounted_run(tmp_path: Path) -> None:
    """The guard end-to-end, not just as a pure function: a friendly that names the
    lecturer touches no transport. `counted` defaults to False on the sender, so a
    caller that forgets to declare a counted series cannot reach him either."""
    sender, transport = make_sender(recipient=(LECTURER_ADDRESS,), lecturer=LECTURER_ADDRESS)
    outcome = sender.send_report(result_path=result_file(tmp_path), role="police")
    assert outcome["action"] == "refuse"
    assert "lecturer" in outcome["reason"]
    assert transport.sends == []


def test_a_counted_run_reaches_the_lecturer(tmp_path: Path) -> None:
    sender, transport = make_sender(
        recipient=(LECTURER_ADDRESS,), lecturer=LECTURER_ADDRESS, lecturer_addressable=True
    )
    outcome = sender.send_report(result_path=result_file(tmp_path), role="police")
    assert outcome["action"] == "send"
    assert transport.sends[0]["to"] == (LECTURER_ADDRESS,)


def test_missing_result_file_refuses_loudly(tmp_path: Path) -> None:
    """A report we cannot read is never a report we invent."""
    sender, transport = make_sender()
    with pytest.raises(FileNotFoundError):
        sender.send_report(result_path=tmp_path / "absent.json", role="police")
    assert transport.sends == []

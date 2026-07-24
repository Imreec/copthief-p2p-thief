"""A report-owing run proves it can deliver BEFORE it plays (M7-10b).

A rehearsal is a counted game minus the counting — the auto-fired report is part of the
format, not an operator afterthought. So the deliverability of that report is decided and
CHECKED before the first sub-game: an empty recipient, a disabled rail, or a stale OAuth
token found after six games have played is the single most expensive moment to find it
(App E rule 35 zeroes both teams for a missing report). `preflight` runs the same interlock
the send runs, plus a credential probe, and raises rather than sending.
"""

from __future__ import annotations

import pytest
from email_fixtures import make_sender

from copthief_core.infra.email_sender import ReportUndeliverableError


def test_a_deliverable_rehearsal_config_passes_and_sends_nothing() -> None:
    sender, transport = make_sender(recipient=("us@x.test", "them@x.test"))
    outcome = sender.preflight()  # must not raise
    assert outcome["action"] == "send"
    assert transport.sends == []  # a probe, never a send
    assert transport.drafts == []


def test_a_disabled_rail_refuses_to_start() -> None:
    sender, _ = make_sender(enabled=False)
    with pytest.raises(ReportUndeliverableError, match="disabled"):
        sender.preflight()


def test_an_empty_recipient_refuses_to_start() -> None:
    sender, _ = make_sender(recipient=())
    with pytest.raises(ReportUndeliverableError, match="no recipient"):
        sender.preflight()


def test_a_rehearsal_addressed_only_to_the_lecturer_refuses_to_start() -> None:
    """The catch moves to the top of the run: a rehearsal that could only reach the
    lecturer is a misconfiguration, and it must never get as far as playing six games."""
    lecturer = "rmisegal+uoh26finalgame@gmail.com"
    sender, _ = make_sender(recipient=(lecturer,), lecturer=lecturer, lecturer_addressable=False)
    with pytest.raises(ReportUndeliverableError, match="counted"):
        sender.preflight()


def test_a_counted_run_may_preflight_with_the_lecturer() -> None:
    lecturer = "rmisegal+uoh26finalgame@gmail.com"
    sender, _ = make_sender(recipient=(lecturer,), lecturer=lecturer, lecturer_addressable=True)
    assert sender.preflight()["action"] == "send"


def test_a_transport_that_cannot_ready_itself_refuses_to_start() -> None:
    """The stale-token case, the real reason this exists: the credential probe runs at
    preflight, and its failure refuses the series before a single game is played."""
    sender, transport = make_sender(recipient=("us@x.test",))

    def broken() -> None:
        raise FileNotFoundError("token.json")

    transport.verify_ready = broken  # type: ignore[attr-defined]
    with pytest.raises(ReportUndeliverableError, match="token.json"):
        sender.preflight()


def test_a_ready_transport_probe_is_honoured() -> None:
    sender, transport = make_sender(recipient=("us@x.test",))
    called: list[bool] = []
    transport.verify_ready = lambda: called.append(True)  # type: ignore[attr-defined]
    sender.preflight()
    assert called == [True]  # the probe ran
    assert transport.sends == []  # but nothing was sent

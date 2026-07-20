"""M7-6 email interlock (ADR-0008; PRD_reporting §5a): authorization IS the recipient.

The per-send arming retype is gone — App E rule 32 requires automatic reporting and
rule 35 zeroes BOTH teams when one side fails to report, so a post-game human step is a
sanction, not a safety. What replaces it is mechanical and more specific than a boolean:
nothing leaves without an address Imree configured for that run. The whole space is
enumerated over (enabled × mode × recipients) and every no-recipient combination refuses.
"""

from __future__ import annotations

from itertools import product

import pytest

from copthief_core.report.email_interlock import decide_email_action

TO = ("imreeyal.copthief@gmail.com",)
PAIR = ("imreeyal.copthief@gmail.com", "peer.team@example.com")
NONE: tuple[str, ...] = ()


@pytest.mark.parametrize(
    ("enabled", "mode", "recipients", "action"),
    [
        (False, "send", TO, "refuse"),  # disabled beats everything
        (False, "draft", TO, "refuse"),
        (True, "send", NONE, "refuse"),  # no configured address = no authorization
        (True, "draft", NONE, "refuse"),
        (True, "send", ("",), "refuse"),  # a blank address is not an address
        (True, "send", ("   ",), "refuse"),  # nor is whitespace
        (True, "send", TO, "send"),  # the counted/friendly path: automatic
        (True, "send", PAIR, "send"),  # friendly report exchange: us + the opponent
        (True, "draft", TO, "draft"),  # retained for a compose-scoped token
        (True, "yolo", TO, "refuse"),  # unknown mode never acts
    ],
)
def test_interlock_truth_table(
    enabled: bool, mode: str, recipients: tuple[str, ...], action: str
) -> None:
    decision = decide_email_action(enabled=enabled, mode=mode, recipients=recipients)
    assert decision.action == action
    if action == "refuse":
        assert decision.reason  # every refusal names its reason (loud, logged)


def test_nothing_acts_without_a_configured_recipient() -> None:
    """The ADR-0008 guarantee: the recipient is the authorization, so across the WHOLE
    space no empty-recipient combination ever reaches a transport."""
    acting = [
        (enabled, mode, recipients)
        for enabled, mode, recipients in product(
            (True, False), ("draft", "send", "other"), (NONE, ("",), TO)
        )
        if decide_email_action(enabled=enabled, mode=mode, recipients=recipients).action != "refuse"
    ]
    assert acting == [(True, "draft", TO), (True, "send", TO)]


def test_refusal_reasons_are_specific_not_generic() -> None:
    """A refusal must name which gate closed — a vague one gets 'debugged' by re-running
    with more permissions, which is exactly the wrong reflex."""
    assert "disabled" in decide_email_action(enabled=False, mode="send", recipients=TO).reason
    assert "recipient" in decide_email_action(enabled=True, mode="send", recipients=NONE).reason
    assert "mode" in decide_email_action(enabled=True, mode="yolo", recipients=TO).reason

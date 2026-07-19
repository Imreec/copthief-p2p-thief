"""M6-4 arming interlock (constraint #16; PRD_reporting §5): mechanical, not vigilance.

The decision is a pure function and the whole space is enumerated: across every
(enabled × mode × arming) combination EXACTLY ONE sends — enabled, mode="send",
and the operator retyped the exact game_uid being reported. Draft mode never
sends regardless of arming; nothing is recipient-specific (arming gates WHETHER,
never WHERE).
"""

from __future__ import annotations

from itertools import product

import pytest

from copthief_core.report.email_interlock import decide_email_action

UID = "f757f50d-d4f4-17e7-06cf-755905739b16"


@pytest.mark.parametrize(
    ("enabled", "mode", "armed", "action"),
    [
        (False, "draft", None, "refuse"),
        (False, "send", UID, "refuse"),  # disabled beats everything, even armed
        (True, "draft", None, "draft"),
        (True, "draft", UID, "draft"),  # draft NEVER sends, arming irrelevant
        (True, "send", None, "refuse"),  # send without arming refuses loudly
        (True, "send", "wrong-uid", "refuse"),  # retyped uid must match exactly
        (True, "send", UID, "send"),  # the one and only sending combination
        (True, "yolo", UID, "refuse"),  # unknown mode never sends
    ],
)
def test_interlock_truth_table(enabled: bool, mode: str, armed: str | None, action: str) -> None:
    decision = decide_email_action(enabled=enabled, mode=mode, armed=armed, game_uid=UID)
    assert decision.action == action
    if action == "refuse":
        assert decision.reason  # every refusal names its reason (loud, logged)


def test_exactly_one_combination_in_the_whole_space_sends() -> None:
    sends = [
        (enabled, mode, armed)
        for enabled, mode, armed in product(
            (True, False), ("draft", "send", "other"), (None, UID, "wrong")
        )
        if decide_email_action(enabled=enabled, mode=mode, armed=armed, game_uid=UID).action
        == "send"
    ]
    assert sends == [(True, "send", UID)]

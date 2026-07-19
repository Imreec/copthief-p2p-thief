"""The email arming interlock (M6-4; constraint #16): mechanical, not vigilance.

A pure total function over (enabled × mode × arming): across the WHOLE space
exactly one combination sends — enabled, mode="send", and the operator retyped
the exact game_uid of the series being reported. Draft mode never sends
regardless of arming; the recipient is not consulted (arming gates WHETHER a
send happens, never WHERE — PRD_reporting §5). Nothing here talks to Gmail:
`infra/email_sender` acts on the decision, through the email gatekeeper.
"""

from __future__ import annotations

from dataclasses import dataclass

MODE_DRAFT = "draft"
MODE_SEND = "send"


@dataclass(frozen=True)
class EmailDecision:
    """What the sender is allowed to do, and (on refusal) exactly why not."""

    action: str  # "draft" | "send" | "refuse"
    reason: str  # empty on draft/send; the loud, logged explanation on refuse


def decide_email_action(
    *, enabled: bool, mode: str, armed: str | None, game_uid: str
) -> EmailDecision:
    """The interlock (Input: [email] state + the arming retype + the reported
    series' game_uid; Output: the one permitted action).

    No email ever leaves without Imree's explicit per-send word — mechanically:
    the word IS the retyped game_uid arriving as `armed`.
    """
    if not enabled:
        return EmailDecision(action="refuse", reason="email disabled (email.enabled=false)")
    if mode == MODE_DRAFT:
        return EmailDecision(action="draft", reason="")
    if mode != MODE_SEND:
        return EmailDecision(action="refuse", reason=f"unknown email.mode {mode!r}")
    if armed is None:
        return EmailDecision(action="refuse", reason="send requires the arming retype (--arm)")
    if armed != game_uid:
        return EmailDecision(
            action="refuse",
            reason=f"arming mismatch: armed {armed!r} != reported game_uid {game_uid!r}",
        )
    return EmailDecision(action="send", reason="")

"""The email interlock (M7-6; ADR-0008): authorization IS the configured recipient.

A pure total function over (enabled × mode × recipients). The M6-4 per-send arming
retype is deliberately gone: App E **rule 32** requires automatic reporting (absence
voids that game's points) and **rule 35** disqualifies the game for BOTH teams when one
side fails to report, so a post-game human step is a sanction rather than a safety —
book §9.3 states outright that at game end "there is no longer room for human
intervention". Runaway protection is the gatekeeper (rule 28, M6-5), which is the book's
own answer to the flood scenario it raises in that same section.

What survives is more specific than the boolean it replaces: **nothing acts without an
address the operator configured for that run**. A generic "sending is allowed" flag says
only that sending may happen; a recipient says who receives it, and nobody types the
lecturer's address by accident. Nothing here talks to Gmail — `infra/email_sender` acts
on the decision, through the email gatekeeper.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

MODE_DRAFT = "draft"
MODE_SEND = "send"


@dataclass(frozen=True)
class EmailDecision:
    """What the sender is allowed to do, and (on refusal) exactly why not."""

    action: str  # "draft" | "send" | "refuse"
    reason: str  # empty on draft/send; the loud, logged explanation on refuse


def decide_email_action(
    *,
    enabled: bool,
    mode: str,
    recipients: Sequence[str],
    lecturer_addressable: bool = False,
    lecturer: str = "",
) -> EmailDecision:
    """The interlock (Input: `[email]` state, the run's configured recipients, whether
    whether the lecturer may be addressed at all, and his address; Output: the one
    permitted action).

    Two guarantees, both mechanical. **No email is ever sent to an address Imree has not
    configured for that run** — an empty or blank recipient list reaches no transport at
    all. And **the lecturer is addressable only from a counted series**:
    `lecturer_addressable` comes from `RunMode.counted_series` (M7-9), which cannot exist
    without `strict_rules` — so he is reachable only from a constitution the App F rows
    have vetted as a genuine six-mini-game match (PRD_engine §6.1). The parameter is named
    for what it PERMITS rather than for the run type, because handing this layer the rules
    flag by mistake is precisely the defect M7-9 removes: a rehearsal arms the full
    rulebook and still cannot reach him. Friendlies pay no ceremony for it.
    """
    if not enabled:
        return EmailDecision(action="refuse", reason="email disabled (email.enabled=false)")
    if mode not in (MODE_DRAFT, MODE_SEND):
        return EmailDecision(action="refuse", reason=f"unknown email.mode {mode!r}")
    addresses = [address.strip() for address in recipients if address.strip()]
    if not addresses:
        return EmailDecision(
            action="refuse",
            reason="no recipient configured for this run (email.recipient is empty)",
        )
    if lecturer.strip() and not lecturer_addressable:
        wanted = lecturer.strip().casefold()
        if any(address.casefold() == wanted for address in addresses):
            return EmailDecision(
                action="refuse",
                reason=(
                    f"the lecturer ({lecturer.strip()}) is addressable only from a counted "
                    "series — this run is not counted"
                ),
            )
    return EmailDecision(action=mode, reason="")

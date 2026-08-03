"""Assembling the report rail (M6-4/M7-9), split from email_sender (150-line rule).

Extracted so the self-play series and the live series build the identical rail
(CLAUDE.md §1 #11): the quota is the signed daily cap, and `lecturer_addressable`
defaults closed so a caller that forgets cannot reach him.
"""

from __future__ import annotations

from copthief_core.infra.email_sender import EmailSender, EmailTransport
from copthief_core.shared.config_model import PrivateSettings, RateLimits

__all__ = ["build_report_sender"]


def build_report_sender(
    *,
    private: PrivateSettings,
    limits: RateLimits,
    transport: EmailTransport | None = None,
    lecturer_addressable: bool = False,
) -> EmailSender:
    """Assemble the report rail the one way (Input: the private settings carrying
    `[email]`, the operational limits, and whether this run may address the lecturer;
    Output: a sender whose gatekeeper holds the daily cap)."""
    from copthief_core.shared.gatekeeper_build import build_gatekeeper

    return EmailSender(
        settings=private.email,
        gatekeeper=build_gatekeeper("email", limits, quota_units=limits.email_daily_cap),
        transport=transport,
        lecturer_addressable=lecturer_addressable,
    )

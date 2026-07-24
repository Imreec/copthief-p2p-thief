"""The report email adapter (M6-4; PRD_reporting §5): interlocked, gatekept.

Byte discipline (PLAN §4): the body is the result artifact READ FROM DISK — the
emailed bytes ARE the file bytes by construction, never a re-serialization.
Every transport call passes through the email gatekeeper (quota → bucket →
breaker, M6-5); a refusal touches no transport at all and names its reason.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol

from copthief_core.report.email_interlock import decide_email_action
from copthief_core.shared.config_model import EmailSettings, PrivateSettings, RateLimits
from copthief_core.shared.gatekeeper import ApiGatekeeper


class EmailTransport(Protocol):
    """What the sender needs from a mail backend (GmailTransport or a test fake)."""

    def create_draft(
        self, *, to: Sequence[str], subject: str, body: str, attachment_name: str | None = None
    ) -> None: ...

    def send(
        self, *, to: Sequence[str], subject: str, body: str, attachment_name: str | None = None
    ) -> None: ...


def build_report_sender(
    *,
    private: PrivateSettings,
    limits: RateLimits,
    transport: EmailTransport | None = None,
    lecturer_addressable: bool = False,
) -> EmailSender:
    """Assemble the report rail the one way (Input: the private settings carrying
    `[email]`, the operational limits, and whether this run may address the lecturer;
    Output: a sender whose gatekeeper holds the daily cap).

    Extracted so the self-play series and the live series build the identical rail
    (CLAUDE.md §1 #11): the quota is the signed daily cap, and `lecturer_addressable`
    defaults closed so a caller that forgets cannot reach him (M7-9).
    """
    from copthief_core.shared.gatekeeper_build import build_gatekeeper

    return EmailSender(
        settings=private.email,
        gatekeeper=build_gatekeeper("email", limits, quota_units=limits.email_daily_cap),
        transport=transport,
        lecturer_addressable=lecturer_addressable,
    )


def report_subject(result: dict[str, Any], role: str) -> str:
    """The reference's exact subject form; a series tie degrades to "tie"."""
    winner = result.get("final_result", {}).get("winner_group") or "tie"
    return f"Police-Thief series result: winner {winner} (reported by {role})"


class EmailSender:
    """Send/draft the result artifact under the interlock, through the gatekeeper."""

    def __init__(
        self,
        *,
        settings: EmailSettings,
        gatekeeper: ApiGatekeeper,
        transport: EmailTransport | None = None,
        lecturer_addressable: bool = False,
    ) -> None:
        from copthief_core.infra.gmail import GmailTransport

        self._settings = settings
        self._gatekeeper = gatekeeper
        # Defaults to False so a caller that forgets to say cannot address the lecturer.
        # M7-9: this is RunMode.lecturer_addressable, NOT the rules flag.
        self._lecturer_addressable = lecturer_addressable
        self._transport: EmailTransport = (
            transport
            if transport is not None
            else GmailTransport(sender=settings.sender, token_path=settings.token_path)
        )

    def send_report(self, *, result_path: Path, role: str) -> dict[str, Any]:
        """One report email attempt (Input: result artifact path + our role; Output:
        `{action, reason, game_uid, recipients}` — action is what actually happened:
        "send" | "draft" | "refuse").

        Automatic by design (App E rule 32; rule 35 zeroes both teams on a missing
        report). The authorization is the configured recipient, so a run with none
        refuses before any transport is touched; every act logs where it went.
        """
        raw = result_path.read_bytes()  # FileNotFoundError is the loud refusal
        result = json.loads(raw.decode("utf-8"))
        game_uid = str(result.get("game_uid", ""))
        recipients = self._settings.recipient
        decision = decide_email_action(
            enabled=self._settings.enabled,
            mode=self._settings.mode,
            recipients=recipients,
            lecturer_addressable=self._lecturer_addressable,
            lecturer=self._settings.lecturer,
        )
        outcome = {
            "action": decision.action,
            "reason": decision.reason,
            "game_uid": game_uid,
            "recipients": list(recipients),
        }
        if decision.action == "refuse":
            return outcome
        body = raw.decode("utf-8")  # body bytes == file bytes (PLAN §4 pin)
        call = self._transport.create_draft if decision.action == "draft" else self._transport.send
        self._gatekeeper.execute(
            call,
            to=recipients,
            subject=report_subject(result, role),
            body=body,
            attachment_name=result_path.name,  # App E rule 34: attached JSON file
        )
        return outcome

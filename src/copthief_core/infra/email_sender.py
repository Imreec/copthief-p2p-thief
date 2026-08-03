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
from copthief_core.shared.config_model import EmailSettings
from copthief_core.shared.gatekeeper import ApiGatekeeper


class ReportUndeliverableError(RuntimeError):
    """A report-owing run cannot deliver its report (M7-10b).

    Raised by `preflight` BEFORE any sub-game plays, so a rehearsal or counted series
    that could not report — empty recipient, disabled rail, stale OAuth token — refuses
    to start rather than playing six games and then failing to report (App E rule 35).
    """


class EmailTransport(Protocol):
    """What the sender needs from a mail backend (GmailTransport or a test fake)."""

    def create_draft(
        self,
        *,
        to: Sequence[str],
        subject: str,
        body: str,
        attachment_name: str | None = None,
        extra_attachments: Sequence[tuple[str, bytes]] = (),
    ) -> None: ...

    def send(
        self,
        *,
        to: Sequence[str],
        subject: str,
        body: str,
        attachment_name: str | None = None,
        extra_attachments: Sequence[tuple[str, bytes]] = (),
    ) -> None: ...


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

    def preflight(self) -> dict[str, Any]:
        """Prove a report COULD be sent, without sending one (Output: `{action,
        recipients}`; Raises: ReportUndeliverableError).

        Runs the same interlock the send runs — so an empty recipient, a disabled rail,
        or the lecturer configured for a rehearsal all refuse here — then probes the
        transport's credentials (`verify_ready`, when it has one) so a stale OAuth token
        is caught before the first sub-game, not after the sixth. What must be decided is
        decided before the series (App E rule 32; rule 35 makes the late discovery
        costliest).
        """
        decision = decide_email_action(
            enabled=self._settings.enabled,
            mode=self._settings.mode,
            recipients=self._settings.recipient,
            lecturer_addressable=self._lecturer_addressable,
            lecturer=self._settings.lecturer,
        )
        if decision.action == "refuse":
            raise ReportUndeliverableError(decision.reason)
        verify = getattr(self._transport, "verify_ready", None)
        if callable(verify):
            try:
                verify()
            except Exception as failure:  # noqa: BLE001 - any credential failure is one outcome
                raise ReportUndeliverableError(
                    f"the report transport is not ready: {type(failure).__name__}: {failure}"
                ) from failure
        return {"action": decision.action, "recipients": list(self._settings.recipient)}

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
            # M7-40 (Round 29, supersedes M7-37's superset): the mail is result-only
            # again — the chatbot's direct ruling, the reference's own emit_series
            # ("returns the result for emailing") and pair symmetry with the opponent
            # team, who flipped first. The other three template types stay visible in
            # the REPOS (the agreed exit criterion), never in the mail. What rode
            # stays visible in every runner log.
            "attachments": [result_path.name],
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

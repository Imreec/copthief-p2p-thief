"""The report email adapter (M6-4; PRD_reporting §5): interlocked, gatekept.

Byte discipline (PLAN §4): the body is the result artifact READ FROM DISK — the
emailed bytes ARE the file bytes by construction, never a re-serialization.
Every transport call passes through the email gatekeeper (quota → bucket →
breaker, M6-5); a refusal touches no transport at all and names its reason.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from copthief_core.report.email_interlock import decide_email_action
from copthief_core.shared.config_model import EmailSettings
from copthief_core.shared.gatekeeper import ApiGatekeeper


class EmailTransport(Protocol):
    """What the sender needs from a mail backend (GmailTransport or a test fake)."""

    def create_draft(self, *, to: str, subject: str, body: str) -> None: ...

    def send(self, *, to: str, subject: str, body: str) -> None: ...


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
    ) -> None:
        from copthief_core.infra.gmail import GmailTransport

        self._settings = settings
        self._gatekeeper = gatekeeper
        self._transport: EmailTransport = (
            transport
            if transport is not None
            else GmailTransport(sender=settings.sender, token_path=settings.token_path)
        )

    def send_report(
        self, *, result_path: Path, role: str, armed: str | None = None
    ) -> dict[str, Any]:
        """One report email attempt (Input: result artifact path + our role + the
        operator's arming retype; Output: `{action, reason, game_uid}` — action is
        what actually happened: "draft" | "send" | "refuse")."""
        raw = result_path.read_bytes()  # FileNotFoundError is the loud refusal
        result = json.loads(raw.decode("utf-8"))
        game_uid = str(result.get("game_uid", ""))
        decision = decide_email_action(
            enabled=self._settings.enabled,
            mode=self._settings.mode,
            armed=armed,
            game_uid=game_uid,
        )
        outcome = {"action": decision.action, "reason": decision.reason, "game_uid": game_uid}
        if decision.action == "refuse":
            return outcome
        body = raw.decode("utf-8")  # body bytes == file bytes (PLAN §4 pin)
        subject = report_subject(result, role)
        call = self._transport.create_draft if decision.action == "draft" else self._transport.send
        self._gatekeeper.execute(call, to=self._settings.recipient, subject=subject, body=body)
        return outcome

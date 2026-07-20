"""Gmail transport (M7-6; App A; ADR-0008; HW6 salvage adapted per porting rule).

The scope is `gmail.send` **only** — App E rule 30 and App A §1.3/§3 mandate it, with
code disqualification as the sanction. M6-4 held `gmail.compose` because the draft rail
needed it (`gmail.send` cannot create a draft — verified against Google's API reference:
`users.drafts.create` accepts only `mail.google.com`/`gmail.modify`/`gmail.compose`).
ADR-0008 dropped draft as an operating posture, which lets the mandated scope be
satisfied *literally* instead of by argument. `create_draft` is retained for a
compose-scoped token but is unreachable on the shipped one.

The report travels twice in one message: as the plain-text body (reference-mirrored,
bytes identical to the artifact on disk) and as an **attached JSON file** (rule 34,
whose sanction for a non-JSON report is score zero). The Google SDK imports lazily
inside the live paths — keyless CI never needs it; only `build_raw` runs offline.
OAuth material (`token.json`, `client_secret*.json`) is git-ignored; the one-time
consent lives in `scripts/gmail_auth.py`.
"""

from __future__ import annotations

import base64
from collections.abc import Sequence
from dataclasses import dataclass
from email.mime.application import MIMEApplication  # stdlib email (absolute import)
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

# Send-only per App E rule 30 + App A; CLAUDE.md §4 reverted alongside this module.
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


@dataclass
class GmailTransport:
    """Send a JSON report (body + attachment) via the Gmail API using an OAuth token."""

    sender: str
    token_path: str = "token.json"  # git-ignored OAuth token (never committed)

    def build_raw(
        self,
        *,
        to: Sequence[str],
        subject: str,
        body: str,
        attachment_name: str | None = None,
    ) -> str:
        """The base64url-encoded RFC-822 message Gmail's API expects (pure, no SDK).

        Input: recipients (joined into one `To` header — scope does not constrain their
        count), subject, the artifact bytes as text, and the artifact filename when it
        should also ride as an attachment. Output: the base64url string.
        """
        message = MIMEMultipart()
        message["To"] = ", ".join(to)
        message["From"] = self.sender
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain", "utf-8"))
        if attachment_name is not None:
            part = MIMEApplication(body.encode("utf-8"), _subtype="json")
            part.add_header("Content-Disposition", "attachment", filename=attachment_name)
            message.attach(part)
        return base64.urlsafe_b64encode(message.as_bytes()).decode()

    def _service(self) -> Any:  # noqa: ANN401 - google client is untyped  # pragma: no cover - live
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)  # type: ignore[no-untyped-call, unused-ignore]
        return build("gmail", "v1", credentials=creds)

    def create_draft(  # pragma: no cover - live
        self,
        *,
        to: Sequence[str],
        subject: str,
        body: str,
        attachment_name: str | None = None,
    ) -> None:
        """Park the report as a Gmail draft — retained for a compose-scoped token, and
        unreachable on the shipped send-only one (Gmail would refuse it)."""
        raw = self.build_raw(to=to, subject=subject, body=body, attachment_name=attachment_name)
        service = self._service()
        service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()

    def send(  # pragma: no cover - live
        self,
        *,
        to: Sequence[str],
        subject: str,
        body: str,
        attachment_name: str | None = None,
    ) -> None:
        """Deliver via the Gmail API — reachable only with a configured recipient."""
        raw = self.build_raw(to=to, subject=subject, body=body, attachment_name=attachment_name)
        service = self._service()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()

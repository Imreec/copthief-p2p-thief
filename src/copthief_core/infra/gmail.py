"""Gmail transport (M6-4; App A; HW6 salvage adapted per porting rule).

D1=A (PR #43): the scope is `gmail.compose` — create/send drafts and messages,
NO mailbox read — the least privilege that supports the draft rail (drafts land
IN Gmail where the operator reviews the literal bytes). The Google SDK imports
lazily inside the live paths: keyless CI never needs it; only `build_raw`
(pure MIME → base64url) runs offline. OAuth material (`token.json`,
`client_secret*.json`) is git-ignored; the one-time consent lives in
`scripts/gmail_auth.py` (OI-5, the dedicated team account).
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from email.mime.text import MIMEText  # stdlib email (absolute import)
from typing import Any

# Compose scope per the D1=A ruling; CLAUDE.md §4 amended alongside this module.
SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]


@dataclass
class GmailTransport:
    """Draft/send a JSON-only body via the Gmail API using an OAuth token file."""

    sender: str
    token_path: str = "token.json"  # git-ignored OAuth token (never committed)

    def build_raw(self, *, to: str, subject: str, body: str) -> str:
        """The base64url-encoded RFC-822 message Gmail's API expects (pure, no SDK)."""
        message = MIMEText(body, "plain", "utf-8")
        message["To"] = to
        message["From"] = self.sender
        message["Subject"] = subject
        return base64.urlsafe_b64encode(message.as_bytes()).decode()

    def _service(self) -> Any:  # noqa: ANN401 - google client is untyped  # pragma: no cover - live
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)  # type: ignore[no-untyped-call, unused-ignore]
        return build("gmail", "v1", credentials=creds)

    def create_draft(self, *, to: str, subject: str, body: str) -> None:  # pragma: no cover - live
        """Park the report as a Gmail draft (the unarmed rail's terminal state)."""
        raw = self.build_raw(to=to, subject=subject, body=body)
        service = self._service()
        service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()

    def send(self, *, to: str, subject: str, body: str) -> None:  # pragma: no cover - live
        """Deliver via the Gmail API — reachable ONLY through the armed interlock."""
        raw = self.build_raw(to=to, subject=subject, body=body)
        service = self._service()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()

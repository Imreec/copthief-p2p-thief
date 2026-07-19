"""One-time Gmail OAuth consent -> token.json (M6-4, OI-5) - live, operator-run, off-CI.

Run ONCE, logged into the DEDICATED TEAM GMAIL ACCOUNT (D1 ruling record on cop
PR #43), after downloading a Desktop OAuth client as `client_secret.json`:

    uv run --group email-live python scripts/gmail_auth.py

Grants the `gmail.compose` scope (create/send drafts, no mailbox read) and writes
the authorized-user credentials to `token.json` for GmailTransport. Re-run to
refresh or replace. Reads GOOGLE_CLIENT_SECRET_FILE (default `client_secret.json`)
and writes GOOGLE_TOKEN_FILE (default `token.json`) - BOTH git-ignored, never
committed (CLAUDE.md constraint #6). The scope is imported from the transport so
consent and use can never disagree.
"""

from __future__ import annotations

import os
from pathlib import Path

from copthief_core.infra.gmail import SCOPES


def main() -> int:
    from google_auth_oauthlib.flow import InstalledAppFlow  # lazy: email-live only

    secret = os.environ.get("GOOGLE_CLIENT_SECRET_FILE", "client_secret.json")
    token = os.environ.get("GOOGLE_TOKEN_FILE", "token.json")
    if not Path(secret).exists():
        raise SystemExit(f"{secret} not found - download the Desktop OAuth client JSON first")
    flow = InstalledAppFlow.from_client_secrets_file(secret, SCOPES)
    creds = flow.run_local_server(port=0)  # opens the browser; throwaway local port
    Path(token).write_text(creds.to_json(), encoding="utf-8")
    print(f"wrote {token} (scopes: {', '.join(SCOPES)}) - git-ignored, keep it secret")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

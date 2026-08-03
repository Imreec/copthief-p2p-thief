"""Archived-log fixtures shared by the series-artifact suites (M7-4).

One builder for a settled sub-game log, used by both the artifact-rebuild suite and the
live-series driver suite (CLAUDE.md §1 #11). The inbound turns are built through the real
`TurnMessage` so the archived shape is the wire's own by construction — a hand-listed
approximation drifted twice during the rehearsal (session audit B3).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

SERIES_LENGTH = 6


def inbound_turn(step: int) -> dict[str, Any]:
    """One archived inbound turn, in the wire's exact shape."""
    from copthief_core.wire.turn import TurnMessage

    return TurnMessage(
        step=step,
        sender="x",
        hint="",
        smell_grid={},
        commit=f"{step:064x}",
        timestamp=f"2026-07-24T12:30:{step:02d}+00:00",
    ).to_wire()


def record(step: int, **payload: object) -> dict[str, Any]:
    """One sealed record as the audit event archives it."""
    return {"payload": {"step": step, **payload}, "nonce": f"{step:064d}", "commit": f"{step:064x}"}


def sub_game_log(path: Path, *, role: str, claim: str, outcome: str, steps: int, sub: int) -> Path:
    """Write one SETTLED sub-game log (Input: the path plus what the game decided;
    Output: the path). Settled means it carries both an `audit` and a `peer_result` —
    the two events `summary_from_log` refuses to invent."""
    rows: list[dict[str, Any]] = [
        {"event": "negotiated", "sender": role, "game_uid": "uid-1"},
        {
            "event": "turn",
            "sender": role,
            "message": {"step": 1, "timestamp": "2026-07-24T12:30:00+00:00"},
        },
        *[
            {"event": "turn_received", "receiver": role, "raw": inbound_turn(i)}
            for i in range(1, steps + 1)
        ],
        {
            "event": "audit",
            "payload": {
                "sender": role,
                "result_claim": claim,
                "records": [
                    record(0, type="system_spec", num_games_declared=6, sub_game_number=sub),
                    *[record(i, move="N") for i in range(1, steps + 1)],
                ],
            },
        },
        {
            "event": "peer_result",
            "sender": role,
            "payload": {"outcome": outcome, "steps": steps, "audit_ok": True},
        },
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return path


def six_logs(tmp_path: Path, *, natural_role: str = "thief") -> list[Path]:
    """A whole settled series: the natural role plays the ODD sub-games (F2)."""
    other = "police" if natural_role == "thief" else "thief"
    return [
        sub_game_log(
            tmp_path / f"sg{n}.jsonl",
            role=natural_role if n % 2 else other,
            claim="survival",
            outcome="thief_survival",
            steps=3,
            sub=n,
        )
        for n in range(1, SERIES_LENGTH + 1)
    ]


class RecordingMail:
    """An email transport that records instead of sending.

    A near-twin of the unit suites' `email_fixtures.FakeTransport` lives there rather
    than being imported: this repo's pytest layout puts each test directory on its own
    import path, so a helper is reachable only from its own package.
    """

    def __init__(self, *, fails_with: Exception | None = None) -> None:
        self.sends: list[dict[str, Any]] = []
        self.drafts: list[dict[str, Any]] = []
        # `fails_with` reproduces a backend that accepts the call and then breaks —
        # a stale OAuth token being the case that actually happened.
        self.fails_with = fails_with

    def send(
        self,
        *,
        to: Sequence[str],
        subject: str,
        body: str,
        attachment_name: str | None = None,
        extra_attachments: Sequence[tuple[str, bytes]] = (),
    ) -> None:
        if self.fails_with is not None:
            raise self.fails_with
        self.sends.append(
            {
                "to": tuple(to),
                "subject": subject,
                "body": body,
                "attachment": attachment_name,
                "extra": list(extra_attachments),
            }
        )

    def create_draft(
        self,
        *,
        to: Sequence[str],
        subject: str,
        body: str,
        attachment_name: str | None = None,
        extra_attachments: Sequence[tuple[str, bytes]] = (),
    ) -> None:
        self.drafts.append(
            {
                "to": tuple(to),
                "subject": subject,
                "body": body,
                "attachment": attachment_name,
                "extra": list(extra_attachments),
            }
        )

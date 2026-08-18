"""A stranger's refused push must never rename the pairing (2026-08-18 live incident).

During the bestteam window 11 friendly, an ali-ahm1 process pushed one agreement
into our door mid-series. The wire guard refused it ("wrong opponent"), but
`opponent_identity_from_logs` adopted the FIRST `agreement_received` identity it
found — the stranger's — and every row, score key, and winner column of the
mailed artifact was keyed to a team we never played. In a counted series that is
the rule-35 disagreeing-filings shape, triggerable by any third team's ping.

The rule these tests pin: the launcher's configured opponent is authoritative for
naming; an inbound identity is adopted only when it AGREES with that pairing.
"""

from __future__ import annotations

import json
from pathlib import Path

from copthief_core.report.series_from_logs import opponent_identity_from_logs


def _log(path: Path, *events: dict) -> Path:
    path.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8", newline="\n")
    return path


def test_stranger_identity_is_skipped_for_the_matching_one(tmp_path: Path) -> None:
    log = _log(
        tmp_path / "g01.jsonl",
        {
            "event": "agreement_received",
            "raw": {"identity": {"group_id": "ali-ahm1", "group_name": "Stranger"}},
        },
        {
            "event": "agreement_received",
            "raw": {
                "identity": {
                    "group_id": "bestteam",
                    "group_name": "BestTeam",
                    "counted_games_played": 0,
                }
            },
        },
    )
    captured = opponent_identity_from_logs([log], "bestteam")
    assert captured["group_id"] == "bestteam"
    assert captured["group_name"] == "BestTeam"
    assert captured["counted_games_played"] == 0


def test_stranger_only_logs_keep_the_configured_pairing(tmp_path: Path) -> None:
    log = _log(
        tmp_path / "g01.jsonl",
        {
            "event": "agreement_received",
            "raw": {"identity": {"group_id": "ali-ahm1", "group_name": "Stranger"}},
        },
    )
    captured = opponent_identity_from_logs([log], "bestteam")
    assert captured["group_id"] == "bestteam"
    # A stranger's declaration is not the opponent's: the block stays empty
    # rather than carrying a third team's words into a signed artifact.
    assert captured["group_name"] == ""


def test_matching_identity_in_a_later_log_is_still_found(tmp_path: Path) -> None:
    first = _log(
        tmp_path / "g01.jsonl",
        {
            "event": "agreement_received",
            "raw": {"identity": {"group_id": "ali-ahm1"}},
        },
    )
    second = _log(
        tmp_path / "g02.jsonl",
        {
            "event": "agreement_received",
            "raw": {"identity": {"group_id": "bestteam", "group_name": "BestTeam"}},
        },
    )
    captured = opponent_identity_from_logs([first, second], "bestteam")
    assert captured["group_name"] == "BestTeam"

"""Rebuild a reference-shaped sub-game summary from a committed game log (M7-4).

A live tunnel game runs in its own process and exits; the `PeerSession` that
`build_summary` needs is gone by the time a series is aggregated. The log, however,
carries everything the summary states: our sealed records ride the `audit` event, the
opponent's turns ride `turn_received`, and the settlement verdict rides `peer_result`.
So the series artifact is derivable from committed evidence alone — which is a stronger
property than reading it out of live memory: what we report is exactly what we archived.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from copthief_core.report.summary_from_log import SummaryRebuildError, summary_from_log


def _write(tmp_path: Path, rows: list[dict]) -> Path:
    log = tmp_path / "game.jsonl"
    log.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return log


def _record(step: int, **payload: object) -> dict:
    return {
        "payload": {"step": step, **payload},
        "nonce": f"{step:064d}",
        "commit": f"{step:064x}",
    }


def _log_rows(*, role: str = "thief", outcome: str = "thief_survival") -> list[dict]:
    """A minimal but faithful log: step-0 spec + two game records + one inbound turn."""
    return [
        {"event": "negotiated", "sender": role, "game_uid": "uid-1"},
        {"event": "turn_received", "receiver": role, "raw": {"step": 1, "sender": "police"}},
        {
            "event": "audit",
            "payload": {
                "sender": role,
                "result_claim": "survival",
                "records": [
                    _record(0, type="system_spec", num_games_declared=6, sub_game_number=1),
                    _record(1, move="N"),
                    _record(2, move="S"),
                ],
            },
        },
        {
            "event": "peer_result",
            "sender": role,
            "payload": {"outcome": outcome, "steps": 2, "audit_ok": True},
        },
    ]


def test_the_summary_carries_the_reference_shaped_fields(tmp_path: Path) -> None:
    log = _write(tmp_path, _log_rows())
    summary = summary_from_log(log, sub_game_number=1, group_name="ImreEyal-Thief")

    assert summary["sub_game_number"] == 1
    assert summary["role"] == "thief"
    assert summary["result"] == "survival"
    assert summary["winner"] == "thief"
    assert summary["steps"] == 2  # GAME records only — the step-0 declaration is not a step
    assert summary["group_name"] == "ImreEyal-Thief"
    assert summary["audit"]["passed"] is True


def test_the_step_zero_declaration_leads_the_records_but_is_not_a_step(tmp_path: Path) -> None:
    """M6-3: the sealed spec record rides the audit ahead of the game records, and the
    step math must never count it — the same rule the live summary follows."""
    log = _write(tmp_path, _log_rows())
    summary = summary_from_log(log, sub_game_number=1, group_name="G")

    assert len(summary["records"]) == 3  # spec + 2 game records, all revealed
    assert summary["records"][0]["payload"]["step"] == 0
    assert summary["records"][0]["payload"]["num_games_declared"] == 6
    assert summary["steps"] == 2


def test_the_opponents_turns_are_carried_verbatim_as_history(tmp_path: Path) -> None:
    log = _write(tmp_path, _log_rows())
    summary = summary_from_log(log, sub_game_number=1, group_name="G")

    assert summary["history"] == [{"step": 1, "sender": "police"}]


def test_a_capture_outcome_names_the_police_winner(tmp_path: Path) -> None:
    rows = _log_rows(role="police", outcome="cop_capture")
    rows[2]["payload"]["result_claim"] = "capture"
    log = _write(tmp_path, rows)
    summary = summary_from_log(log, sub_game_number=2, group_name="G")

    assert summary["result"] == "capture"
    assert summary["winner"] == "police"
    assert summary["role"] == "police"


def test_a_log_without_an_audit_cannot_be_summarised(tmp_path: Path) -> None:
    """An aborted game has no revealed records, so it has no honest summary — refuse
    loudly rather than emit a hollow one into a series artifact."""
    rows = [r for r in _log_rows() if r["event"] != "audit"]
    log = _write(tmp_path, rows)
    with pytest.raises(SummaryRebuildError, match="audit"):
        summary_from_log(log, sub_game_number=1, group_name="G")


def test_a_log_without_a_result_cannot_be_summarised(tmp_path: Path) -> None:
    rows = [r for r in _log_rows() if r["event"] != "peer_result"]
    log = _write(tmp_path, rows)
    with pytest.raises(SummaryRebuildError, match="result"):
        summary_from_log(log, sub_game_number=1, group_name="G")


def test_a_sub_game_that_left_no_log_at_all_refuses_the_same_way(tmp_path: Path) -> None:
    """Found in the first live run of the series driver: a child that died before
    writing anything raised a bare FileNotFoundError out of the aggregation, so an
    operator saw a traceback where the design promises a named refusal. A missing log
    is the emptiest case of the same fact — this game has no honest summary."""
    with pytest.raises(SummaryRebuildError, match="no log"):
        summary_from_log(tmp_path / "never_written.jsonl", sub_game_number=1, group_name="G")


def test_the_opponents_revealed_step_zero_commit_is_read(tmp_path: Path) -> None:
    """M7-36: the 16:00 window emitted "unknown" opponent commits while the driver had
    them — the live path rebuilds summaries FROM THE LOG, and the log-side rebuild
    never learned the M7-33 field. Their reveal rides `audit_received`; read it."""
    rows = _log_rows()
    rows.append(
        {
            "event": "audit_received",
            "receiver": "thief",
            "raw": {
                "sender": "police",
                "records": [
                    {
                        "payload": {
                            "step": 0,
                            "type": "step_zero",
                            "github_commit": "ba" * 20,
                        },
                        "nonce": "aa" * 16,
                        "commit": "bb" * 32,
                    }
                ],
            },
        }
    )
    summary = summary_from_log(_write(tmp_path, rows), sub_game_number=1, group_name="G")
    assert summary["opponent_github_commit"] == "ba" * 20


def test_a_log_without_their_audit_leaves_the_opponent_commit_unknown(
    tmp_path: Path,
) -> None:
    summary = summary_from_log(_write(tmp_path, _log_rows()), sub_game_number=1, group_name="G")
    assert summary["opponent_github_commit"] == "unknown"

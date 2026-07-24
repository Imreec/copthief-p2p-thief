"""A whole series artifact rebuilt from committed logs (M7-4).

The live rehearsal plays each sub-game in its own process, so the series result must be
assembled from what was archived rather than from live memory. This pins the join:
N logs -> N reference-shaped summaries -> the emitted artifact set, with the scoring
table doing the arithmetic and the step-0 declarations riding along as evidence.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from copthief_core.report.series_from_logs import series_artifact_from_logs
from copthief_core.report.summary_from_log import SummaryRebuildError
from copthief_core.shared.config import load_all

CONFIG = Path("config")


def _inbound(step: int) -> dict:
    """One archived inbound turn, in the wire's exact ten-key shape."""
    from copthief_core.wire.turn import TurnMessage

    return TurnMessage(
        step=step,
        sender="x",
        hint="",
        smell_grid={},
        commit=f"{step:064x}",
        timestamp=f"2026-07-24T12:30:{step:02d}+00:00",
    ).to_wire()


def _record(step: int, **payload: object) -> dict:
    return {"payload": {"step": step, **payload}, "nonce": f"{step:064d}", "commit": f"{step:064x}"}


def _log(path: Path, *, role: str, claim: str, outcome: str, steps: int, sub: int) -> Path:
    rows = [
        {"event": "negotiated", "sender": role, "game_uid": "uid-1"},
        {
            "event": "turn",
            "sender": role,
            "message": {"step": 1, "timestamp": "2026-07-24T12:30:00+00:00"},
        },
        *[
            # Built through the real TurnMessage so the archived shape is the wire's
            # ten keys by construction, not a hand-listed approximation that drifts.
            {"event": "turn_received", "receiver": role, "raw": _inbound(i)}
            for i in range(1, steps + 1)
        ],
        {
            "event": "audit",
            "payload": {
                "sender": role,
                "result_claim": claim,
                "records": [
                    _record(0, type="system_spec", num_games_declared=6, sub_game_number=sub),
                    *[_record(i, move="N") for i in range(1, steps + 1)],
                ],
            },
        },
        {
            "event": "peer_result",
            "sender": role,
            "payload": {"outcome": outcome, "steps": steps, "audit_ok": True},
        },
    ]
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return path


def _six_logs(tmp_path: Path) -> list[Path]:
    """Alon's alternation: ODD sub-games we are thief, EVEN we are police."""
    logs = []
    for n in range(1, 7):
        role = "thief" if n % 2 else "police"
        logs.append(
            _log(
                tmp_path / f"sg{n}.jsonl",
                role=role,
                claim="survival",
                outcome="thief_survival",
                steps=3,
                sub=n,
            )
        )
    return logs


def test_six_logs_become_one_series_artifact(tmp_path: Path) -> None:
    constitution, private, _ = load_all(CONFIG, counted=False)
    result = series_artifact_from_logs(
        logs=_six_logs(tmp_path),
        constitution=constitution,
        private=private,
        config_dir=CONFIG,
        opponent_group="anrbj666",
        out_root=tmp_path / "out",
    )

    assert result["game_uid"] == "uid-1"
    assert result["num_sub_games"] == 6
    assert len(result["sub_games"]) == 6  # every sub-game represented, none dropped
    assert len(result["groups"]) == 2  # both teams' declaration blocks
    # Roles alternate 3/3, so six survivals must split the series evenly — the scoring
    # table's arithmetic, not ours.
    assert result["final_result"]["sub_games_won"] == {"imreeyal": 3, "anrbj666": 3}
    assert result["final_result"]["series_tie"] is True
    # The whole counted-shaped artifact SET lands on disk, not just the result dict.
    written = {p.name for p in (tmp_path / "out").rglob("*.json")}
    assert "result_imreeyal-vs-anrbj666.json" in written
    assert "declaration_imreeyal-vs-anrbj666.json" in written
    assert sum(1 for n in written if n.startswith("report_")) == 6


def test_roles_alternate_across_the_rebuilt_series(tmp_path: Path) -> None:
    from copthief_core.report.summary_from_log import summary_from_log

    roles = [
        summary_from_log(p, sub_game_number=i + 1, group_name="G")["role"]
        for i, p in enumerate(_six_logs(tmp_path))
    ]
    assert roles == ["thief", "police", "thief", "police", "thief", "police"]


def test_an_unsettled_log_refuses_the_whole_series(tmp_path: Path) -> None:
    """One hollow sub-game must not silently become a series artifact — a report that
    quietly drops a game is exactly the contradictory report rule 35 punishes."""
    constitution, private, _ = load_all(CONFIG, counted=False)
    logs = _six_logs(tmp_path)
    logs[3].write_text('{"event": "negotiated", "sender": "police"}\n', encoding="utf-8")
    with pytest.raises(SummaryRebuildError):
        series_artifact_from_logs(
            logs=logs,
            constitution=constitution,
            private=private,
            config_dir=CONFIG,
            opponent_group="anrbj666",
            out_root=tmp_path / "out",
        )

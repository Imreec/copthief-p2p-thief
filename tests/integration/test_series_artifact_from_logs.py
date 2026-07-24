"""A whole series artifact rebuilt from committed logs (M7-4).

The live rehearsal plays each sub-game in its own process, so the series result must be
assembled from what was archived rather than from live memory. This pins the join:
N logs -> N reference-shaped summaries -> the emitted artifact set, with the scoring
table doing the arithmetic and the step-0 declarations riding along as evidence.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from series_fixtures import six_logs

from copthief_core.report.series_from_logs import series_artifact_from_logs
from copthief_core.report.summary_from_log import SummaryRebuildError
from copthief_core.shared.config import load_all

CONFIG = Path("config")


def test_six_logs_become_one_series_artifact(tmp_path: Path) -> None:
    constitution, private, _ = load_all(CONFIG, counted=False)
    result = series_artifact_from_logs(
        logs=six_logs(tmp_path),
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
        for i, p in enumerate(six_logs(tmp_path))
    ]
    assert roles == ["thief", "police", "thief", "police", "thief", "police"]


def test_measured_durations_give_each_sub_game_a_real_end_time(tmp_path: Path) -> None:
    """A caller that TIMED the series says so, and the entry stops claiming the game
    ended at the instant it began (the live driver measures; a late rebuild cannot)."""
    constitution, private, _ = load_all(CONFIG, counted=False)
    result = series_artifact_from_logs(
        logs=six_logs(tmp_path),
        constitution=constitution,
        private=private,
        config_dir=CONFIG,
        opponent_group="anrbj666",
        out_root=tmp_path / "out",
        durations=dict.fromkeys(range(1, 7), 42.0),
    )
    entry = result["sub_games"][0]
    assert entry["ended_at"] != entry["started_at"]


def test_an_unsettled_log_refuses_the_whole_series(tmp_path: Path) -> None:
    """One hollow sub-game must not silently become a series artifact — a report that
    quietly drops a game is exactly the contradictory report rule 35 punishes."""
    constitution, private, _ = load_all(CONFIG, counted=False)
    logs = six_logs(tmp_path)
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

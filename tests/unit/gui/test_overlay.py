"""M4-4 belief-vs-truth overlay (PRD_gui_replay §6): post-audit only, metric-identical.

Truth is the opponent's REVEALED audit trajectory; belief history is the logged
snapshots (evidence of what we believed at the time, never a recomputation). Per-step
error is `1 − P(truth_cell)` — the same number `BeliefFilter.belief_error` and the
M3-3 eval tables report.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from copthief_core.gui.models.overlay import overlay_series
from copthief_core.peer.match import run_local_minigame
from copthief_core.shared.jsonl_logger import read_events

CONFIG_DIR = Path("config")


@pytest.fixture(scope="module")
def game_events(tmp_path_factory: pytest.TempPathFactory) -> list[dict[str, Any]]:
    log_path = tmp_path_factory.mktemp("logs") / "game.jsonl"
    run_local_minigame(CONFIG_DIR, police_seed=11, thief_seed=22, log_path=log_path)
    return read_events(log_path)


def test_series_aligns_belief_snapshots_with_the_audited_truth(
    game_events: list[dict[str, Any]],
) -> None:
    series = overlay_series(game_events, role="police")
    beliefs = [
        e["payload"] for e in game_events if e["event"] == "belief" and e["sender"] == "police"
    ]
    thief_records = next(
        e["payload"]["records"]
        for e in game_events
        if e["event"] == "audit" and e["payload"]["sender"] == "thief"
    )
    truth_by_step = {r["payload"]["step"]: tuple(r["payload"]["position"]) for r in thief_records}
    assert series.role == "police"
    assert series.opponent == "thief"
    assert len(series.errors) == len(beliefs) > 0
    for step, error, grid in zip(series.steps, series.errors, series.beliefs, strict=True):
        truth = truth_by_step[step]
        expected = 1.0 - grid.get(f"{truth[0]},{truth[1]}", 0.0)
        assert error == pytest.approx(expected)  # the M3-3 metric, exactly
        assert 0.0 <= error <= 1.0
    assert series.truth_path == [truth_by_step[s] for s in series.steps]


def test_series_refuses_a_log_without_the_opponents_audit(
    game_events: list[dict[str, Any]],
) -> None:
    # Post-audit only (FR-10): no revealed trajectory, no overlay — by refusal,
    # not by silently rendering something else.
    unaudited = [
        e for e in game_events if e["event"] not in ("audit", "audit_answer", "audit_received")
    ]
    with pytest.raises(ValueError, match="audit"):
        overlay_series(unaudited, role="police")


def test_series_detects_the_single_logged_role(game_events: list[dict[str, Any]]) -> None:
    police_only = [
        e for e in game_events if not (e["event"] == "belief" and e["sender"] == "thief")
    ]
    series = overlay_series(police_only, role=None)  # auto-detect from the log
    assert series.role == "police"


def test_png_exports_render_from_a_real_game(
    game_events: list[dict[str, Any]], tmp_path: Path
) -> None:
    from copthief_core.gui.export import export_overlay_pngs
    from copthief_core.shared.config import load_all

    constitution, private, _limits = load_all(CONFIG_DIR, counted=False)
    log_path = tmp_path / "game.jsonl"
    log_path.write_text(
        "\n".join(json.dumps(e, ensure_ascii=False, sort_keys=True) for e in game_events) + "\n",
        encoding="utf-8",
    )
    overlay_png = tmp_path / "overlay.png"
    overlay, curve = export_overlay_pngs(
        log_path,
        overlay_png,
        role="police",
        constitution=constitution,
        settings=private.gui,
    )
    assert overlay == overlay_png
    assert curve == tmp_path / "overlay-curve.png"
    for path in (overlay, curve):
        assert path.exists()
        assert path.stat().st_size > 0
        assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"

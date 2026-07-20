"""M6-6 DoD (PLAN §13 M6): a full local series produces the four valid artifacts.

Two in-process peers play `num_games` (from the SIGNED constitution) with role
alternation over one persistent transport pair; the natural side emits all
artifacts; every per-sub-game log replays Verified OK; the declared game-count
is the truthful signed value (rules 37–38). The mirror side plays under a
clearly-labeled "-mirror" identity (honest self-play, PRD_reporting §6).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from copthief_core.peer.replay import VERDICT_OK, replay_from_log, verdict_for
from copthief_core.report.schemas import validate_artifact
from copthief_core.sdk.series_run import run_local_series

CONFIG_DIR = Path("config")


@pytest.fixture(scope="module")
def series(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """One real two-game local series (module-scoped: the expensive fixture)."""
    root = tmp_path_factory.mktemp("series")
    config_dir = root / "config"
    shutil.copytree(CONFIG_DIR, config_dir)
    game = json.loads((config_dir / "game.json").read_text(encoding="utf-8"))
    game["network_and_league"]["num_games"] = 2  # negotiable key — App F guard allows
    (config_dir / "game.json").write_text(json.dumps(game), encoding="utf-8")
    out_root, log_dir = root / "out", root / "logs"
    outcome = run_local_series(
        config_dir,
        base_police_seed=11,
        base_thief_seed=22,
        out_root=out_root,
        log_dir=log_dir,
    )
    return {"outcome": outcome, "out_root": out_root, "log_dir": log_dir}


def test_all_artifacts_exist_and_validate(series: dict[str, Any]) -> None:
    result = series["outcome"]["result"]
    gid = series["outcome"]["group_id"]
    game_id = result["game_id"]
    folder = series["out_root"] / gid
    for kind, name in [
        ("declaration", f"declaration_{game_id}.json"),
        ("config", f"config_{game_id}_g01.json"),
        ("config", f"config_{game_id}_g02.json"),
        ("log", f"log_{game_id}_g01.json"),
        ("log", f"log_{game_id}_g02.json"),
        ("result", f"result_{game_id}.json"),
    ]:
        data = json.loads((folder / name).read_text(encoding="utf-8"))
        validate_artifact(kind, data)
    # The book-§8 Hebrew reports ride beside the four reference artifacts (D2).
    assert (folder / f"report_{game_id}_g01.json").exists()
    assert (folder / f"report_{game_id}_g02.json").exists()


def test_roles_alternate_across_the_sub_games(series: dict[str, Any]) -> None:
    result = series["outcome"]["result"]
    gid = series["outcome"]["group_id"]
    roles = [sg["roles"][gid] for sg in result["sub_games"]]
    assert roles == ["police", "thief"]  # natural role on odd sub-games (F2)
    assert result["num_sub_games"] == 2


def test_declared_game_count_is_the_signed_truth(series: dict[str, Any]) -> None:
    result = series["outcome"]["result"]
    gid = series["outcome"]["group_id"]
    game_id = result["game_id"]
    log1 = json.loads(
        (series["out_root"] / gid / f"log_{game_id}_g01.json").read_text(encoding="utf-8")
    )
    step0 = log1["records"][0]["payload"]
    assert step0["type"] == "system_spec"
    assert step0["num_games_declared"] == 2  # rules 37–38: sealed, truthful
    assert step0["sub_game_number"] == 1
    declaration = json.loads(
        (series["out_root"] / gid / f"declaration_{game_id}.json").read_text(encoding="utf-8")
    )
    assert declaration["num_sub_games"] == 2


def test_every_sub_game_log_replays_verified_ok(series: dict[str, Any]) -> None:
    logs = sorted(series["log_dir"].glob("*.jsonl"))
    assert len(logs) == 2
    for log in logs:
        assert verdict_for(replay_from_log(log)) == VERDICT_OK


def test_email_rail_is_wired_and_resting_state_refuses(series: dict[str, Any]) -> None:
    email = series["outcome"]["email"]
    assert email["action"] == "refuse"  # shipped default: enabled=false (constraint #16)
    assert "disabled" in email["reason"]


def test_mutual_audits_pass_on_both_sides_every_game(series: dict[str, Any]) -> None:
    for side in ("natural", "mirror"):
        for result in series["outcome"][side + "_results"]:
            assert result["audit_ok"] is True

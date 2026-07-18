"""M4-3 replay walk model (PRD_gui_replay §5): the viewer's step cursor, pure.

Post-audit data only: frames are built from REVEALED audit records — showing the
objective board retrospectively is legal (rules 8–9 constrain the live view; book §7.2
draws exactly this line).
"""

import json
from pathlib import Path
from typing import Any

import pytest

from copthief_core.gui.models.replay import ReplayWalk
from copthief_core.peer.match import run_local_minigame
from copthief_core.peer.replay import VERDICT_OK, VERDICT_TAMPERED
from copthief_core.shared.jsonl_logger import read_events

CONFIG_DIR = Path("config")


@pytest.fixture(scope="module")
def real_log(tmp_path_factory: pytest.TempPathFactory) -> Path:
    log_path = tmp_path_factory.mktemp("logs") / "game.jsonl"
    run_local_minigame(CONFIG_DIR, police_seed=11, thief_seed=22, log_path=log_path)
    return log_path


def test_walk_builds_verified_frames_from_a_real_log(real_log: Path) -> None:
    walk = ReplayWalk.from_log(real_log)
    assert walk.verdict == VERDICT_OK
    assert len(walk) > 0
    events = read_events(real_log)
    records = {
        e["payload"]["sender"]: e["payload"]["records"] for e in events if e["event"] == "audit"
    }
    last = walk.frame(len(walk) - 1)
    for role in ("police", "thief"):
        revealed_last = records[role][-1]["payload"]
        if revealed_last["step"] == last.step:  # the shorter side may end one earlier
            assert list(last.positions[role] or ()) == revealed_last["position"]


def test_walk_cursor_steps_forward_and_back_with_clamping(real_log: Path) -> None:
    walk = ReplayWalk.from_log(real_log)
    assert walk.index == 0
    walk.back()
    assert walk.index == 0  # clamped at the start
    walk.forward()
    assert walk.index == 1
    for _ in range(len(walk) * 2):
        walk.forward()
    assert walk.index == len(walk) - 1  # clamped at the end


def test_walk_over_a_tampered_log_still_builds_but_carries_the_banner(
    real_log: Path, tmp_path: Path
) -> None:
    events: list[dict[str, Any]] = read_events(real_log)
    audit = next(e for e in events if e["event"] == "audit")
    audit["payload"]["records"][0]["payload"]["position"] = [0, 0]
    mutated = tmp_path / "tampered.jsonl"
    mutated.write_text(
        "\n".join(json.dumps(e, ensure_ascii=False, sort_keys=True) for e in events) + "\n",
        encoding="utf-8",
    )
    walk = ReplayWalk.from_log(mutated)
    assert walk.verdict == VERDICT_TAMPERED
    assert walk.problems  # the viewer shows WHAT failed alongside the red banner
    assert len(walk) > 0  # the timeline still renders under the banner

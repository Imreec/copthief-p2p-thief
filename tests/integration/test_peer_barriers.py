"""Full-loop outbound barriers (M5-2; PRD_police_brain §7): wall → wire → audit → replay.

A local mini-game with a barrier-placing police brain (ref-police at coin-flip 1.0,
selected through the real config path incl. `[strategy.police]` options) must place
walls on the wire, keep both sides' audits Verified OK, and replay clean from the log —
the constraint-#13 evidence that the sealed-record shape change breaks nothing.
"""

import json
import re
import shutil
from pathlib import Path

import pytest

from copthief_core.peer.match import run_local_minigame
from copthief_core.peer.replay import replay_from_log


@pytest.fixture
def waller_config(tmp_path: Path) -> Path:
    """The shipped config tree with the police brain swapped to an always-wall ref-police.

    Role-agnostic rewrite (PR #29 rule): each repo ships its own `police_class`, so the
    KEY is matched, never a literal value; the options section may or may not exist.
    """
    config = tmp_path / "config"
    shutil.copytree(Path("config"), config)
    toml_path = config / "game.toml"
    text, hits = re.subn(
        r'police_class = "[^"]*"',
        'police_class = "ref-police"',
        toml_path.read_text(encoding="utf-8"),
    )
    assert hits == 1, "game.toml lost its police_class key"
    if "[strategy.police]" in text:
        text = text.replace(
            "[strategy.police]", "[strategy.police]\nref_police_barrier_chance = 1.0"
        )
    else:
        text += "\n[strategy.police]\nref_police_barrier_chance = 1.0\n"
    toml_path.write_text(text, encoding="utf-8")
    return config


def test_walling_police_keeps_mutual_audit_and_replay_green(
    waller_config: Path, tmp_path: Path
) -> None:
    log_path = tmp_path / "game.jsonl"
    result = run_local_minigame(waller_config, police_seed=3, thief_seed=4, log_path=log_path)
    assert result.audit_ok_police_side
    assert result.audit_ok_thief_side
    assert "BARRIER" in result.police_moves  # the wall really played
    walls = [
        event["message"]["barrier_placed"]
        for event in map(json.loads, log_path.read_text(encoding="utf-8").splitlines())
        if event.get("event") == "turn" and event.get("sender") == "police"
        if event["message"].get("barrier_placed") is not None
    ]
    assert walls  # barrier_placed rode the wire outbound
    summary = replay_from_log(log_path)
    assert summary.verified, summary.problems  # Verified OK: barrier turns re-verify

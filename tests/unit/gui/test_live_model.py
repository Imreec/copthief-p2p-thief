"""M4-2 live view-model (PRD_gui_replay §4): pure fold over the v1.1 event stream.

Local truth only, BY CONSTRUCTION: the model consumes nothing but the logged event
stream, exposes no opponent-position field, and the module imports no full-information
(referee) machinery — App E rules 8–9 pinned structurally, not by discipline.
"""

import ast
from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest

from copthief_core.domain.state_machine import GameState
from copthief_core.gui.models.live import (
    BANNER_LOCKED,
    BANNER_YOUR_TURN,
    LiveViewModel,
    LiveViewState,
    heat_color,
)
from copthief_core.peer.match import run_local_minigame
from copthief_core.shared.config import load_all
from copthief_core.shared.jsonl_logger import read_events

CONFIG_DIR = Path("config")
CONSTITUTION, _PRIVATE, _LIMITS = load_all(CONFIG_DIR, counted=False)


def _model(role: str) -> LiveViewModel:
    start = CONSTITUTION.board.cop_start if role == "police" else CONSTITUTION.board.thief_start
    return LiveViewModel(role=role, board=CONSTITUTION.board.make_board(), start=start)


@pytest.fixture(scope="module")
def game_events(tmp_path_factory: pytest.TempPathFactory) -> list[dict[str, Any]]:
    log_path = tmp_path_factory.mktemp("logs") / "game.jsonl"
    run_local_minigame(CONFIG_DIR, police_seed=11, thief_seed=22, log_path=log_path)
    return read_events(log_path)


def test_banner_is_your_turn_only_while_computing() -> None:
    model = _model("police")
    for state in GameState:
        model.apply(
            {
                "event": "transition",
                "sender": "police",
                "payload": {"from": "waiting_for_opponent", "to": state.value, "trigger": ""},
            }
        )
        view = model.state()
        if state is GameState.COMPUTING_MOVE:
            assert (view.banner, view.banner_color) == (BANNER_YOUR_TURN, "green")
        elif state in (GameState.GAME_OVER, GameState.TECHNICAL_LOSS):
            assert view.finished
        else:
            assert (view.banner, view.banner_color) == (BANNER_LOCKED, "gray")


def test_heat_color_is_anchored_and_monotone_in_probability() -> None:
    low, high = "#ffffff", "#c81e1e"
    assert heat_color(0.0, low=low, high=high) == low
    assert heat_color(1.0, low=low, high=high) == high
    shades = [heat_color(p / 10, low=low, high=high) for p in range(11)]
    reds_kept = [int(s[1:3], 16) - int(s[3:5], 16) for s in shades]
    assert reds_kept == sorted(reds_kept)  # deeper red ⇒ higher probability (book fig. 9)


def test_fold_over_a_real_game_matches_the_audited_truth(
    game_events: list[dict[str, Any]],
) -> None:
    for role in ("police", "thief"):
        model = _model(role)
        for event in game_events:
            model.apply(event)
        view = model.state()
        records = next(
            e["payload"]["records"]
            for e in game_events
            if e["event"] == "audit" and e["payload"]["sender"] == role
        )
        # The folded own position must equal the last sealed (audited) position.
        assert list(view.own_position) == records[-1]["payload"]["position"]
        assert view.step == records[-1]["payload"]["step"]
        last_belief = [
            e["payload"] for e in game_events if e["event"] == "belief" and e["sender"] == role
        ][-1]
        assert view.belief == last_belief["grid"]
        assert view.finished
        assert view.hint_out == records[-1]["payload"]["hint"]


def test_declared_barriers_accumulate_from_both_directions() -> None:
    model = _model("thief")
    model.apply(
        {
            "event": "turn_received",
            "receiver": "thief",
            "raw": {"step": 1, "sender": "police", "barrier_placed": [2, 3]},
        }
    )
    model.apply(
        {
            "event": "turn",
            "sender": "thief",
            "message": {"step": 1, "hint": "hiding", "barrier_placed": None},
        }
    )
    view = model.state()
    assert (2, 3) in view.barriers
    assert view.hint_in == ""  # a message without a hint key contributes nothing
    assert view.hint_out == "hiding"


def test_other_roles_events_never_touch_this_view() -> None:
    model = _model("police")
    model.apply(
        {
            "event": "belief",
            "sender": "thief",
            "payload": {"step": 3, "grid": {"0,0": 1.0}, "argmax": "0,0"},
        }
    )
    view = model.state()
    assert view.belief == {}
    assert view.step == 0


def test_view_state_structurally_cannot_carry_the_opponent_position() -> None:
    names = {f.name for f in fields(LiveViewState)}
    assert not any("opponent" in n or "truth" in n for n in names)
    source = Path("src/copthief_core/gui/models/live.py").read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom | ast.Import):
            imported = getattr(node, "module", "") or ""
            targets = [imported, *[a.name for a in node.names]]
            assert not any("referee" in t or "match" in t for t in targets), (
                "gui.models.live must never import full-information machinery"
            )

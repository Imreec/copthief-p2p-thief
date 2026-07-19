"""M1-8 DoD: an M1 mini-game is replayable — and re-verifiable — from its JSONL log alone."""

import json
from pathlib import Path

from copthief_core.peer.match import run_local_minigame
from copthief_core.peer.replay import replay_from_log

CONFIG_DIR = Path("config")


def test_logged_minigame_replays_verified(tmp_path: Path) -> None:
    log_path = tmp_path / "game.jsonl"
    result = run_local_minigame(CONFIG_DIR, police_seed=11, thief_seed=22, log_path=log_path)
    summary = replay_from_log(log_path)
    assert summary.verified
    assert summary.problems == []
    assert summary.steps == result.steps
    assert summary.outcome == result.outcome
    assert summary.game_uid == result.game_uid
    assert summary.moves["police"] == list(result.police_moves)
    assert summary.moves["thief"] == list(result.thief_moves)


def test_tampered_log_record_is_detected(tmp_path: Path) -> None:
    log_path = tmp_path / "game.jsonl"
    run_local_minigame(CONFIG_DIR, police_seed=11, thief_seed=22, log_path=log_path)
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    for index, line in enumerate(lines):
        event = json.loads(line)
        if event["event"] == "audit":
            # Rewrite history at GAME step 3 — selected by step, not list index (the
            # M6-3 step-0 declaration record leads the list).
            record = next(r for r in event["payload"]["records"] if r["payload"].get("step") == 3)
            record["payload"]["move"] = "MOVE:N"
            lines[index] = json.dumps(event, ensure_ascii=False)
            break
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary = replay_from_log(log_path)
    assert not summary.verified
    assert any("step 3" in p for p in summary.problems)


def test_reveal_must_match_the_hint_that_traveled(tmp_path: Path) -> None:
    # The audit's revealed hint must equal the hint sent in-game — a divergence is flagged.
    log_path = tmp_path / "game.jsonl"
    run_local_minigame(CONFIG_DIR, police_seed=11, thief_seed=22, log_path=log_path)
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    for index, line in enumerate(lines):
        event = json.loads(line)
        if event["event"] == "turn" and event["sender"] == "police":
            event["message"]["hint"] = "a hint that never traveled"
            lines[index] = json.dumps(event, ensure_ascii=False)
            break
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary = replay_from_log(log_path)
    assert not summary.verified
    assert any("hint" in p for p in summary.problems)

"""JSONL event log (PLAN §7): one canonical-JSON record per line, append-only, lossless."""

from pathlib import Path

from copthief_core.shared.jsonl_logger import JsonlEventLogger, read_events


def test_events_round_trip_losslessly(tmp_path: Path) -> None:
    log_path = tmp_path / "game.jsonl"
    logger = JsonlEventLogger(log_path)
    logger.log({"event": "negotiate", "payload": {"terms": {"board_size": 7}}})
    logger.log({"event": "turn", "sender": "police", "message": {"hint": "אני ליד הכיכר"}})
    events = read_events(log_path)
    assert len(events) == 2
    assert events[0]["payload"]["terms"]["board_size"] == 7
    assert events[1]["message"]["hint"] == "אני ליד הכיכר"


def test_log_is_one_json_object_per_line_and_appends(tmp_path: Path) -> None:
    log_path = tmp_path / "game.jsonl"
    JsonlEventLogger(log_path).log({"event": "a"})
    JsonlEventLogger(log_path).log({"event": "b"})  # a second logger appends, never truncates
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert all(line.startswith("{") and line.endswith("}") for line in lines)


def test_logger_creates_missing_parent_directories(tmp_path: Path) -> None:
    # The M3 thief-repo trap: pointing a fresh log at docs/evidence/ before the
    # directory exists must work, not crash (PRD_gui_replay §3).
    log_path = tmp_path / "docs" / "evidence" / "fresh.jsonl"
    JsonlEventLogger(log_path).log({"event": "a"})
    assert read_events(log_path) == [{"seq": 1, "event": "a"}]


def test_each_event_gains_a_monotonic_sequence_number(tmp_path: Path) -> None:
    log_path = tmp_path / "game.jsonl"
    logger = JsonlEventLogger(log_path)
    for name in ("x", "y", "z"):
        logger.log({"event": name})
    assert [e["seq"] for e in read_events(log_path)] == [1, 2, 3]

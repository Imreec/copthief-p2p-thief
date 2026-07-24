"""Each sub-game of a live series is its own process (M7-4).

The command is built by a pure function so the thing that must be right — the real
sub-game index, the alternating role, and the run's governance reaching the child — is
pinned keyless. A wrong index here is unrepairable: it is sealed into the step-0 commit
from the game's first instant (rules 37-38), which is exactly what the 2026-07-24
rehearsal sealed six times over.
"""

from __future__ import annotations

import sys
from pathlib import Path

from copthief_core.sdk.subgame_process import subgame_command
from copthief_core.shared.run_mode import RunMode

DEV = RunMode()


def _command(mode: RunMode = DEV, *, sub_game_number: int = 4) -> list[str]:
    return subgame_command(
        role="thief",
        config_dir=Path("config"),
        seed=11,
        host="127.0.0.1",
        port=8802,
        opponent_url="https://thief.example.test/mcp",
        log_path=Path("logs/g04.jsonl"),
        sub_game_number=sub_game_number,
        mode=mode,
    )


def _value(command: list[str], flag: str) -> str:
    return command[command.index(flag) + 1]


def test_the_child_plays_the_named_sub_game_in_the_named_role() -> None:
    command = _command()
    assert _value(command, "--sub-game") == "4"
    assert _value(command, "--role") == "thief"
    assert _value(command, "--log") == str(Path("logs/g04.jsonl"))
    assert _value(command, "--opponent-url") == "https://thief.example.test/mcp"


def test_the_child_is_our_own_interpreter_running_our_own_cli() -> None:
    command = _command()
    assert command[:3] == [sys.executable, "-m", "copthief_core.sdk.cli"]
    assert command[3:5] == ["run", "peer"]


def test_a_rehearsal_arms_the_rulebook_in_the_child_too() -> None:
    """The child loads the config itself, so a driver that armed App F only in its own
    process would play six games under the disarmed loader — the M7-9 defect, moved."""
    assert "--rehearsal" in _command(RunMode.rehearsal())
    assert "--counted" not in _command(RunMode.rehearsal())


def test_a_counted_series_says_so_to_the_child() -> None:
    assert "--counted" in _command(RunMode.counted())
    assert "--rehearsal" not in _command(RunMode.counted())


def test_a_dev_run_carries_no_governance_flag_at_all() -> None:
    command = _command()
    assert "--rehearsal" not in command
    assert "--counted" not in command


def test_a_child_that_dies_records_its_exit_code_and_why(tmp_path: Path) -> None:
    """Found in the first live run: five sub-games "played" in three seconds because
    their children failed at launch, and the run record said only `outcome: unknown`.
    A driver that cannot say WHY a sub-game did not happen cannot be operated."""
    from copthief_core.sdk.subgame_process import play_subgame

    result = play_subgame(
        [sys.executable, "-c", "import sys; print('boom', file=sys.stderr); sys.exit(3)"]
    )
    assert result["outcome"] == "unknown"
    assert result["exit_code"] == 3
    assert "boom" in result["stderr"]


def test_a_child_that_finishes_reports_its_own_verdict(tmp_path: Path) -> None:
    from copthief_core.sdk.subgame_process import play_subgame

    result = play_subgame(
        [sys.executable, "-c", 'print(\'{"outcome": "cop_capture", "audit_ok": true}\')']
    )
    assert result["outcome"] == "cop_capture"
    assert result["audit_ok"] is True
    assert result["exit_code"] == 0

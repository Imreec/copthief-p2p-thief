"""App F guard (PRD_engine §4–§5): fixed/minimum/negotiable statuses, counted-series scope."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from copthief_core.shared.appf_guard import AppFTable, validate_constitution

CONFIG_DIR = Path("config")


@pytest.fixture(scope="module")
def table() -> AppFTable:
    return AppFTable.load(CONFIG_DIR / "app_f_table.json")


@pytest.fixture
def game() -> dict[str, Any]:
    raw: dict[str, Any] = json.loads((CONFIG_DIR / "game.json").read_text(encoding="utf-8"))
    return copy.deepcopy(raw)


def test_shipped_defaults_pass_the_guard(table: AppFTable, game: dict[str, Any]) -> None:
    assert validate_constitution(game, table, counted=False) == []


def test_fixed_value_deviation_is_refused(table: AppFTable, game: dict[str, Any]) -> None:
    game["scoring"]["capture_cop"] = 25
    violations = validate_constitution(game, table, counted=False)
    assert any("scoring.capture_cop" in v for v in violations)


def test_lowering_a_minimum_is_refused(table: AppFTable, game: dict[str, Any]) -> None:
    game["movement_and_barriers"]["max_barriers"] = 10
    violations = validate_constitution(game, table, counted=False)
    assert any("max_barriers" in v for v in violations)


def test_raising_a_minimum_is_accepted(table: AppFTable, game: dict[str, Any]) -> None:
    game["board_and_agents"]["grid_size"] = 9
    assert validate_constitution(game, table, counted=False) == []


def test_negotiable_values_accept_any_agreement(table: AppFTable, game: dict[str, Any]) -> None:
    game["world"]["map_area"] = "Haifa"
    game["board_and_agents"]["thief_start"] = [5, 5]
    game["network_and_league"]["response_timeout_sec"] = 10
    assert validate_constitution(game, table, counted=False) == []


def test_missing_parameter_is_refused(table: AppFTable, game: dict[str, Any]) -> None:
    del game["movement_and_barriers"]["survival_threshold"]
    violations = validate_constitution(game, table, counted=False)
    assert any("survival_threshold" in v for v in violations)


def test_sample_num_games_allowed_only_outside_counted_series(
    table: AppFTable, game: dict[str, Any]
) -> None:
    # Set explicitly rather than read from the shipped file: the committed constitution
    # is the LEAGUE one (six, App F) since 2026-07-24, and this test pins the RULE — a
    # single-sample constitution is legal outside a counted series and illegal inside it.
    game["network_and_league"]["num_games"] = 1  # the App B single-sample default
    assert validate_constitution(game, table, counted=False) == []
    violations = validate_constitution(game, table, counted=True)
    assert any("num_games" in v for v in violations)


def test_counted_series_of_six_minigames_passes(table: AppFTable, game: dict[str, Any]) -> None:
    game["network_and_league"]["num_games"] = 6
    assert validate_constitution(game, table, counted=True) == []


def test_non_numeric_value_for_a_minimum_parameter_is_refused(
    table: AppFTable, game: dict[str, Any]
) -> None:
    game["movement_and_barriers"]["max_barriers"] = "many"
    violations = validate_constitution(game, table, counted=False)
    assert any("max_barriers" in v and "numeric" in v for v in violations)


def test_changing_the_fixed_move_set_is_refused(table: AppFTable, game: dict[str, Any]) -> None:
    game["movement_and_barriers"]["move_set"] = ["N", "S", "E", "W", "STAY", "NE"]
    violations = validate_constitution(game, table, counted=False)
    assert any("move_set" in v for v in violations)

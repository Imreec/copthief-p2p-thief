"""Config loading (PRD_engine §5; App B): guard-gated, version-validated, typed.

The constitution is sourced EXCLUSIVELY from `game.json` — the strongest form of the
App B overlay rule ("JSON overlays TOML on shared keys"): a private TOML key can never
even reach a signed term. The App F guard runs on every load; a violation refuses the
load loudly (ConfigError lists every problem) instead of playing an illegal game.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from copthief_core.domain.scoring import ScoringTable
from copthief_core.shared.appf_guard import AppFTable, validate_constitution
from copthief_core.shared.config_model import (
    BoardParams,
    Constitution,
    GatekeeperParams,
    LeagueParams,
    MovementParams,
    PheromoneParams,
    PrivateSettings,
    RateLimits,
    WorldParams,
)
from copthief_core.shared.gazetteer_loader import load_gazetteer as load_gazetteer
from copthief_core.shared.limits_loader import load_rate_limits as load_rate_limits
from copthief_core.shared.private_config import ConfigError as ConfigError
from copthief_core.shared.private_config import load_private_settings as load_private_settings


def _pair(raw: list[int]) -> tuple[int, int]:
    """A JSON [row, col] array as a Coord tuple."""
    return (raw[0], raw[1])


def load_constitution(path: Path, table: AppFTable, *, counted: bool) -> Constitution:
    """Load + guard-validate the signed shared config (Input: game.json path, App F table;
    Output: typed Constitution; Raises: ConfigError listing every App F violation)."""
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    violations = validate_constitution(raw, table, counted=counted)
    if violations:
        raise ConfigError("App F guard refused the constitution:\n" + "\n".join(violations))
    board, world = raw["board_and_agents"], raw["world"]
    movement, league, gate = (
        raw["movement_and_barriers"],
        raw["network_and_league"],
        raw["rate_limiter_gatekeeper"],
    )
    return Constitution(
        schema_version=str(raw["schema_version"]),
        agreed_between=(str(raw["agreed_between"][0]), str(raw["agreed_between"][1])),
        board=BoardParams(
            grid_size=board["grid_size"],
            num_agents=board["num_agents"],
            thief_start=_pair(board["thief_start"]),
            cop_start=_pair(board["cop_start"]),
            axis_origin_corner=board["axis_origin_corner"],
            axis_start_index=board["axis_start_index"],
        ),
        world=WorldParams(map_area=world["map_area"], hint_max_words=world["hint_max_words"]),
        movement=MovementParams(
            move_set=tuple(movement["move_set"]),
            max_barriers=movement["max_barriers"],
            max_moves=movement["max_moves"],
            survival_threshold=movement["survival_threshold"],
        ),
        scoring=ScoringTable(**raw["scoring"]),
        pheromones=PheromoneParams(
            center_intensity=raw["pheromones"]["pheromone_center_intensity"],
            decay=raw["pheromones"]["pheromone_decay"],
            grid_size=raw["pheromones"]["pheromone_grid_size"],
            # Emission gate, reference schema-1.3 key (M2 F4): signed value when the
            # shared file carries it, App F table default otherwise.
            min_center_intensity=raw["pheromones"].get(
                "pheromone_min_center_intensity",
                table.entries["pheromones.min_center_intensity"].default,
            ),
        ),
        league=LeagueParams(**league),
        gatekeeper=GatekeeperParams(**gate),
    )


def load_all(
    config_dir: Path, *, counted: bool
) -> tuple[Constitution, PrivateSettings, RateLimits]:
    """One-call startup load of the whole config tree, guard-gated and version-checked."""
    table = AppFTable.load(config_dir / "app_f_table.json")
    constitution = load_constitution(config_dir / "game.json", table, counted=counted)
    private = load_private_settings(config_dir / "game.toml")
    limits = load_rate_limits(config_dir / "rate_limits.json", constitution.gatekeeper)
    return constitution, private, limits

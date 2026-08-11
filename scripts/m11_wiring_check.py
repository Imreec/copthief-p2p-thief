"""M11 wiring audit (throwaway): armed knobs reach the brains via real loaders."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from copthief_core.shared.private_config import load_private_settings  # noqa: E402
from copthief_core.strategy.doctrine_evader import DEFAULT_OPTIONS  # noqa: E402
from copthief_core.strategy.evader_cage import CAGE_DEFAULTS  # noqa: E402

ARMED_THIEF = {
    "room_first": 1.0,
    "cage_escape": 1.0,
    "forecast_walls": 3.0,
    "forecast_wall_reach": 2.0,
    "flight_floor": 2.0,
    "center_margin_cap": 2.0,
}

merged = {**DEFAULT_OPTIONS, **CAGE_DEFAULTS, **ARMED_THIEF}
assert merged["cage_escape"] == 1.0
assert merged["center_margin_cap"] == 2.0
print("thief merge path OK:", {k: merged[k] for k in ARMED_THIEF})

settings = load_private_settings(Path("config/game.toml"))
police = settings.strategy_options("police")
keys = ("contain_enabled", "contain_range", "path_distance", "claim_threshold")
print(f"cop game.toml v{settings.version} ->", {k: police[k] for k in keys})
overlay = settings.police_model_options.get("multiplicative_book_v1", {})
pins = ("contain_enabled", "contain_range", "path_distance")
print("book-v1 overlay pins:", {k: overlay[k] for k in pins})

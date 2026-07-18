"""Private per-peer TOML loading (App B §4), split from shared/config (150-line rule).

Constitution keys that stray into the TOML are simply ignored — JSON overlays TOML on
shared keys, so a private key can never even reach a signed term.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

from copthief_core.shared.config_model import GuiSettings, PrivateSettings

_VERSION_FORM = re.compile(r"^\d+\.\d{2}$")


class ConfigError(Exception):
    """A config file is unloadable: guard violation, bad version, or broken precedence."""


def validated_version(raw: dict[str, Any], source: str) -> str:
    """Validated `version` field (CLAUDE.md §1 #9: starts 1.00, checked at startup)."""
    value = raw.get("version")
    if not isinstance(value, str) or not _VERSION_FORM.match(value):
        raise ConfigError(f"{source}: version must match N.NN, got {value!r}")
    return value


def load_private_settings(path: Path) -> PrivateSettings:
    """Load the per-peer TOML (Input: game.toml path; Output: typed PrivateSettings;
    Raises: ConfigError on a malformed version)."""
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    game, network = raw.get("game", {}), raw.get("network", {})
    belief, strategy = raw.get("belief", {}), raw.get("strategy", {})
    gui = raw.get("gui", {})
    return PrivateSettings(
        version=validated_version(raw, path.name),
        group_name=str(game["group_name"]),
        group_id=str(game["group_id"]),
        sub_game_number=int(game["sub_game_number"]),
        members=tuple(str(m) for m in game.get("members", [])),
        repos={str(k): str(v) for k, v in game.get("repos", {}).items()},
        mcp_servers={str(k): str(v) for k, v in game.get("mcp_servers", {}).items()},
        llm_model=str(game.get("llm_model", "")),
        my_port=int(network["my_port"]),
        opponent_url=str(network["opponent_url"]),
        turn_timeout_seconds=float(network["turn_timeout_seconds"]),
        poll_interval_seconds=float(network["poll_interval_seconds"]),
        connect_timeout_seconds=float(network["connect_timeout_seconds"]),
        smell_trust_weight=float(belief["smell_trust_weight"]),
        hint_trust_default=float(belief["hint_trust_default"]),
        police_class=str(strategy["police_class"]),
        thief_class=str(strategy["thief_class"]),
        police_options={str(k): float(v) for k, v in strategy.get("police", {}).items()},
        thief_options={str(k): float(v) for k, v in strategy.get("thief", {}).items()},
        gui=GuiSettings(
            refresh_ms=int(gui["refresh_ms"]),
            cell_px=int(gui["cell_px"]),
            heat_low=str(gui["heat_low"]),
            heat_high=str(gui["heat_high"]),
            png_dpi=int(gui["png_dpi"]),
            font_family=str(gui["font_family"]),
            font_size=int(gui["font_size"]),
            theme_bg=str(gui["theme_bg"]),
            theme_panel=str(gui["theme_panel"]),
            theme_fg=str(gui["theme_fg"]),
            accent=str(gui["accent"]),
        ),
    )

"""Private per-peer TOML loading (App B §4), split from shared/config (150-line rule).

Constitution keys that stray into the TOML are simply ignored — JSON overlays TOML on
shared keys, so a private key can never even reach a signed term.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

from copthief_core.shared.config_model import EmailSettings, GuiSettings, PrivateSettings
from copthief_core.shared.locked_models import (
    DEFAULT_SCENT_MODEL,
    LockedModelRegistry,
    load_locked_models,
)

_VERSION_FORM = re.compile(r"^\d+\.\d{2}$")


class ConfigError(Exception):
    """A config file is unloadable: guard violation, bad version, or broken precedence."""


def _recipients(raw: Any) -> tuple[str, ...]:  # noqa: ANN401 - raw TOML value
    """`email.recipient` as a tuple (Input: a list, a bare string, or nothing; Output:
    the non-blank addresses). A bare string stays valid so a single-recipient config
    needs no brackets; blanks are dropped here so the interlock sees a clean list."""
    values = raw if isinstance(raw, list | tuple) else [raw]
    return tuple(str(v).strip() for v in values if str(v).strip())


def validated_version(raw: dict[str, Any], source: str) -> str:
    """Validated `version` field (CLAUDE.md §1 #9: starts 1.00, checked at startup)."""
    value = raw.get("version")
    if not isinstance(value, str) or not _VERSION_FORM.match(value):
        raise ConfigError(f"{source}: version must match N.NN, got {value!r}")
    return value


def load_private_settings(
    path: Path, *, locked_models: LockedModelRegistry | None = None
) -> PrivateSettings:
    """Load the per-peer TOML (Input: game.toml path, optionally the already-loaded
    locked-model registry; Output: typed PrivateSettings; Raises: ConfigError on a
    malformed version).

    The registry is a property of the config TREE, not of this file, so `load_all`
    passes it in and requires it. Called bare — parsing a TOML in isolation — we fall
    back to the sibling file and then to an empty registry: a handshake still refuses to
    declare an unregistered model, so nothing can be silently declared wrong.
    """
    if locked_models is None:
        sibling = path.parent / "locked_models.json"
        locked_models = (
            load_locked_models(sibling) if sibling.is_file() else LockedModelRegistry("", {})
        )
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    game, network = raw.get("game", {}), raw.get("network", {})
    belief, strategy = raw.get("belief", {}), raw.get("strategy", {})
    gui, email = raw.get("gui", {}), raw.get("email", {})
    scent = raw.get("scent", {})
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
        profile_hint_floor=float(belief["profile_hint_floor"]),
        police_class=str(strategy["police_class"]),
        thief_class=str(strategy["thief_class"]),
        police_options={str(k): float(v) for k, v in strategy.get("police", {}).items()},
        thief_options={str(k): float(v) for k, v in strategy.get("thief", {}).items()},
        hint_bank=str(strategy.get("hint_bank", "")),
        # M3-8 (ADR-0004 v2): omission keeps the reference form, so a config that never
        # heard of named models plays exactly what M3-2 shipped. The registry lives
        # beside the TOML because its docs are hashed, not interpreted.
        scent_model=str(scent.get("model", DEFAULT_SCENT_MODEL)),
        scent_physics_tolerance=float(scent.get("physics_tolerance", 0.0)),
        locked_models=locked_models,
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
        # M7-6 (ADR-0008): omission of [email] still yields the safe resting state —
        # disabled with NO recipient, so the interlock cannot be weakened by absence.
        # `recipient` accepts a list (friendly = us + the opponent) or a bare string
        # (one address), because the authorization IS the configured recipient.
        email=EmailSettings(
            enabled=bool(email.get("enabled", False)),
            mode=str(email.get("mode", "send")),
            recipient=_recipients(email.get("recipient", ())),
            sender=str(email.get("sender", "")),
            token_path=str(email.get("token_path", "token.json")),
            lecturer=str(email.get("lecturer", "")),
        ),
    )

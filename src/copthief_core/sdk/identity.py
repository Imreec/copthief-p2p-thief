"""The seven-key identity block (F8b shape), split from sdk/series_run (150-line
rule). Consumed by the declaration builders and any live-series caller."""

from __future__ import annotations

from typing import Any

from copthief_core.shared.config_model import PrivateSettings
from copthief_core.shared.sysinfo import collect_spec


def identity_block(private: PrivateSettings) -> dict[str, Any]:
    """One team's identity dict for the whole-series declaration (the same seven
    keys the handshake exchanges; spec from the process-cached sysinfo probes)."""
    return {
        "group_id": private.group_id,
        "group_name": private.group_name,
        "members": list(private.members),
        "repos": dict(private.repos),
        "mcp_servers": dict(private.mcp_servers),
        "llm_model": private.llm_model,
        "spec": collect_spec(),
        # M7-34 (book §9.2.1): the mutual game-count declaration the diversity
        # weighting reads — the opponent team's client already sends theirs.
        "counted_games_played": private.counted_games_played,
    }

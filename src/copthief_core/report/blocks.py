"""Pure building blocks for the artifact builders (PRD_reporting §3).

Interface-mirrored from the reference report helpers @960499fd (ADR-0002): the
declaration's hardware/group blocks, timestamp arithmetic, and the per-group token
series. No I/O, no clock reads — `ended_at` derives from inputs only.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from copthief_core.report.consensus import consensus_signature


def ended_at(started_at: str, duration_seconds: float) -> str:
    """`started_at` (ISO, tz-aware) + duration -> ISO end time; echo unparsable input
    (a malformed timestamp must never crash artifact emission at game end)."""
    try:
        start = datetime.fromisoformat(started_at)
    except (TypeError, ValueError):
        return started_at
    return (start + timedelta(seconds=duration_seconds)).isoformat()


def hardware_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Exactly the six book hardware fields, renaming sysinfo's gpu_type -> gpu_model
    (the declaration schema's key; the sealed step-0 spec keeps the sysinfo names)."""
    return {
        "cpu_type": spec.get("cpu_type"),
        "cpu_freq_mhz": spec.get("cpu_freq_mhz"),
        "cpu_cores": spec.get("cpu_cores"),
        "ram_gb": spec.get("ram_gb"),
        "gpu_model": spec.get("gpu_type"),
        "vram_gb": spec.get("vram_gb"),
    }


def group_block(identity: dict[str, Any]) -> dict[str, Any]:
    """One team's static declaration block from its seven-key handshake identity
    (F8b); signature = consensus over the block sans signature (sign-then-insert)."""
    block = {
        "group_id": identity["group_id"],
        "group_name": identity["group_name"],
        "members": identity["members"],
        "repos": identity["repos"],
        "mcp_servers": identity["mcp_servers"],
        "llm_model": identity["llm_model"],
        "hardware_spec": hardware_spec(identity["spec"]),
    }
    block["signature"] = consensus_signature(block)
    return block


def tokens_series(sub_games: list[dict[str, Any]], group_ids: list[str]) -> dict[str, int]:
    """Per-group token totals over all sub-game rows (the result's fairness ledger)."""
    return {g: sum(sg.get("tokens", {}).get(g, 0) for sg in sub_games) for g in group_ids}

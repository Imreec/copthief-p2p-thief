"""Post-game analysis flows, split from the SimulationSdk facade (150-line rule, M7-14).

Input: the sdk (for config + settings) and a committed log; Output: replay verdicts
and overlay renders. GUI imports stay lazy — the viz group is an analysis-time
dependency (D2), never a peer-runtime one.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from copthief_core.peer.replay import ReplaySummary, replay_from_log

if TYPE_CHECKING:
    from copthief_core.sdk.simulation import SimulationSdk


def replay_flow(sdk: SimulationSdk, log_path: Path, *, gui: bool = False) -> ReplaySummary:
    """Re-verify a logged game (M4-3): the cryptographic walk over every record.

    With `gui`, the viewer window (verdict banner + step controls) opens and blocks
    until closed; the summary is returned either way."""
    summary = replay_from_log(log_path)
    if gui:
        from copthief_core.gui.windows.replay import show_replay

        show_replay(log_path, sdk.constitution, sdk.private.gui)
    return summary


def export_overlay_flow(
    sdk: SimulationSdk, log_path: Path, out: Path, *, role: str | None = None
) -> tuple[Path, Path]:
    """Render the belief-vs-truth overlay + error curve PNGs from an audited log
    (M4-4; post-audit only). Returns (overlay path, curve path)."""
    from copthief_core.gui.export import export_overlay_pngs

    return export_overlay_pngs(
        log_path, out, role=role, constitution=sdk.constitution, settings=sdk.private.gui
    )

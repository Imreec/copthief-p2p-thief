"""PNG export of the belief-vs-truth overlay + error curve (PRD_gui_replay §6).

Analysis-time only (matplotlib from the `viz` group, Agg backend — offline, keyless):
match-time code never imports this module. The overlay draws the opponent's revealed
trajectory over the final belief heatmap; the curve plots the per-step `1 − P(truth)`
error — both for the README (App C evidence).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # never require a display — CI-safe by construction
import matplotlib.pyplot as plt

from copthief_core.gui.models.overlay import OverlaySeries, overlay_series
from copthief_core.shared.config_model import Constitution, GuiSettings
from copthief_core.shared.jsonl_logger import read_events


def export_overlay_pngs(
    log_path: Path,
    out: Path,
    *,
    role: str | None,
    constitution: Constitution,
    settings: GuiSettings,
) -> tuple[Path, Path]:
    """Render both PNGs from an audited log (Input: JSONL path + overlay target path +
    whose belief (None = auto-detect) + signed geometry + render knobs; Output:
    (overlay path, curve path — `<out stem>-curve.png` beside it))."""
    series = overlay_series(read_events(log_path), role=role)
    curve = out.with_name(f"{out.stem}-curve{out.suffix}")
    _render_overlay(series, constitution, settings, out)
    _render_curve(series, settings, curve)
    return out, curve


def _grid_matrix(series: OverlaySeries, constitution: Constitution) -> list[list[float]]:
    """The FINAL belief snapshot as a row-major matrix in board coordinates."""
    size, origin = constitution.board.grid_size, constitution.board.axis_start_index
    final = series.beliefs[-1]
    return [
        [final.get(f"{row + origin},{col + origin}", 0.0) for col in range(size)]
        for row in range(size)
    ]


def _render_overlay(
    series: OverlaySeries, constitution: Constitution, settings: GuiSettings, out: Path
) -> None:
    origin = constitution.board.axis_start_index
    flip = constitution.board.axis_origin_corner.startswith("bottom")
    figure, axes = plt.subplots()
    axes.imshow(
        _grid_matrix(series, constitution),
        cmap="Reds",
        origin="lower" if flip else "upper",
        vmin=0.0,
    )
    cols = [c - origin for _, c in series.truth_path]
    rows = [r - origin for r, _ in series.truth_path]
    axes.plot(cols, rows, marker="o", label=f"{series.opponent} audited path")
    axes.plot(cols[-1], rows[-1], marker="*", label="final position")
    axes.set_title(f"{series.role} belief (final) vs {series.opponent} audited truth")
    axes.legend()
    figure.savefig(out, dpi=settings.png_dpi, bbox_inches="tight")
    plt.close(figure)


def _render_curve(series: OverlaySeries, settings: GuiSettings, out: Path) -> None:
    figure, axes = plt.subplots()
    axes.plot(series.steps, series.errors, marker=".")
    axes.set_xlabel("step")
    axes.set_ylabel("belief error  (1 - P(truth))")
    axes.set_ylim(0.0, 1.0)
    axes.set_title(f"{series.role} belief error vs audited {series.opponent} position")
    figure.savefig(out, dpi=settings.png_dpi, bbox_inches="tight")
    plt.close(figure)

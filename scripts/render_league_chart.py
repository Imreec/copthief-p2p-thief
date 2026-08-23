"""Render the league-campaign chart from the banked counted-series artifacts (M8-1).

Reads every `result_*.json` under reports/counted-series/imreeyal/ — the same
artifacts the lecturer holds — and draws the ten series as paired horizontal
bars (our score vs the opponent's), ordered by our own played-count field.
Nothing is hand-entered; re-run after any new counted series. Palette is
dark-surface categorical, validated (CVD dE >= 24, contrast >= 3:1).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # never require a display
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "reports" / "counted-series" / "imreeyal"
US = "imreeyal"
# Display-only theme (mirrors config/game.toml [gui]) + the validated pair.
BG, PANEL, FG, MUTED = "#0f172a", "#1e293b", "#e2e8f0", "#94a3b8"
C_US, C_THEM = "#0284c7", "#b45309"


def load_series() -> list[dict]:
    """All counted results, in play order (Input: none; Output: list of
    {opponent, ours, theirs, won, tie, diversity} sorted by our ledger count)."""
    rows = []
    for path in sorted(RESULTS.glob("result_*.json")):
        final = json.loads(path.read_text(encoding="utf-8"))["final_result"]
        opponent = next(k for k in final["total_score"] if k != US)
        rows.append(
            {
                "opponent": opponent,
                "ours": final["total_score"][US],
                "theirs": final["total_score"][opponent],
                "won": final["winner_group"] == US,
                "tie": final["series_tie"],
                "diversity": final["diversity_reward_applied"][US],
                "order": final["games_played_including_this"][US],
            }
        )
    return sorted(rows, key=lambda r: r["order"])


def render(rows: list[dict], out: Path) -> None:
    """Paired-bar campaign chart (Input: play-ordered rows + target PNG path;
    Output: the chart written to `out`)."""
    figure, axes = plt.subplots(figsize=(9.0, 6.2))
    figure.patch.set_facecolor(BG)
    axes.set_facecolor(BG)
    ys = range(len(rows))
    half = 0.19
    for y, row in zip(ys, rows, strict=True):
        axes.barh(y - half, row["ours"], height=0.34, color=C_US, zorder=3)
        axes.barh(y + half, row["theirs"], height=0.34, color=C_THEM, zorder=3)
        axes.text(row["ours"] + 1.2, y - half, str(row["ours"]), va="center", color=FG, fontsize=9)
        axes.text(
            row["theirs"] + 1.2, y + half, str(row["theirs"]), va="center", color=MUTED, fontsize=9
        )
        tag = "T" if row["tie"] else ("W" if row["won"] else "L")
        star = " +10" if row["diversity"] else ""
        axes.text(97.5, y, f"{tag}{star}", va="center", ha="left", color=FG, fontsize=10)
    axes.set_yticks(list(ys))
    axes.set_yticklabels([f"{i + 1}. {r['opponent']}" for i, r in enumerate(rows)], color=FG)
    axes.invert_yaxis()
    axes.set_xlim(0, 104)
    axes.set_xticks([0, 30, 60, 90])
    axes.tick_params(colors=MUTED, labelsize=9)
    for spine in axes.spines.values():
        spine.set_color(PANEL)
    axes.grid(axis="x", color=PANEL, linewidth=0.8, zorder=0)
    wins = sum(1 for r in rows if r["won"])
    losses = sum(1 for r in rows if not r["won"] and not r["tie"])
    ties = sum(1 for r in rows if r["tie"])
    ours, theirs = sum(r["ours"] for r in rows), sum(r["theirs"] for r in rows)
    bonuses = sum(1 for r in rows if r["diversity"])
    axes.set_title(
        f"League campaign - {len(rows)} counted series (the cap)  |  "
        f"{wins}W-{losses}L-{ties}T  |  points {ours}-{theirs}  |  +10 diversity x{bonuses}",
        color=FG,
        fontsize=11,
        pad=14,
    )
    axes.legend(
        ["ImreEyal", "opponent"],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.06),
        ncols=2,
        facecolor=PANEL,
        edgecolor=PANEL,
        labelcolor=FG,
        fontsize=9,
    )
    figure.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(figure)
    print(f"wrote {out}")


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "assets" / "league-campaign.png"
    render(load_series(), out)

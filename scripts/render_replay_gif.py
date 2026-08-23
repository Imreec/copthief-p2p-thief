"""Animated replay GIF from an audited counted log (M8-1 README evidence).

Renders the belief heatmap + both AUDITED trajectories step by step from a committed
JSONL evidence log — the post-audit data the replay verifier re-hashes, so the
animation is reproducible and tamper-evident. Parsing lives in `replay_gif_data`
(150-line rule). Analysis-time only (viz group: matplotlib + pillow); match-time code
never imports this. Usage: uv run python scripts/render_replay_gif.py --log L --out G.
"""

from __future__ import annotations

import argparse
import io
import sys
import tomllib
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # never require a display
import matplotlib.pyplot as plt
from matplotlib import colors, patches
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from replay_gif_data import barriers_by_step, post_move_path  # noqa: E402

from copthief_core.peer.replay import revealed_records  # noqa: E402
from copthief_core.shared.jsonl_logger import read_events  # noqa: E402

_THIEF_COLOR = "#f59e0b"  # the live GUI's thief marker (display-only)


def render(log: Path, out: Path, size: int, gui: dict[str, Any]) -> None:
    """Write the GIF (Input: audited log + target + board size + [gui] theme)."""
    events = read_events(log)
    beliefs = {
        e["payload"]["step"]: (e["sender"], dict(e["payload"]["grid"]))
        for e in events
        if e["event"] == "belief"
    }
    role = next(iter({sender for sender, _ in beliefs.values()}))
    opponent = "thief" if role == "police" else "police"
    revealed = revealed_records(events)
    ours = post_move_path(revealed.get(role, []))
    theirs = post_move_path(revealed.get(opponent, []))
    walls = barriers_by_step(events)
    result = next((e["payload"] for e in events if e["event"] == "peer_result"), {})
    last = max(ours) if ours else max(beliefs)
    steps = [s for s in sorted(beliefs) if s <= last]  # end on the settled frame
    bg, panel, fg = gui["theme_bg"], gui["theme_panel"], gui["theme_fg"]
    heat = colors.LinearSegmentedColormap.from_list("heat", [gui["heat_low"], gui["heat_high"]])
    marker = {"police": gui["accent"], "thief": _THIEF_COLOR}
    letters = {"police": "P", "thief": "T"}
    figure, axes = plt.subplots(figsize=(5.4, 5.9))
    figure.patch.set_facecolor(bg)

    def frame(index: int) -> None:
        step = steps[min(index, len(steps) - 1)]
        axes.clear()
        axes.set_facecolor(bg)
        _, grid = beliefs[step]
        matrix = [[grid.get(f"{r},{c}", 0.0) for c in range(size)] for r in range(size)]
        axes.imshow(matrix, cmap=heat, origin="upper", vmin=0.0, vmax=1.0)
        for wall_step, (row, col) in walls.items():
            if wall_step <= step:
                axes.add_patch(
                    patches.Rectangle((col - 0.5, row - 0.5), 1, 1, color=panel, ec=fg, lw=1.2)
                )
        for who, path in ((opponent, theirs), (role, ours)):
            if step in path:
                row, col = path[step]
                axes.plot(col, row, "o", color=marker[who], markersize=22, zorder=5)
                axes.text(col, row, letters[who], ha="center", va="center", color=bg, zorder=6)
        done = index >= len(steps) - 1
        title = (
            f"{result.get('outcome', 'settled')} @ step {result.get('steps', step)} - audit "
            f"{'OK' if result.get('audit_ok') else '?'}"
            if done
            else f"step {step}  ({role} belief)"
        )
        axes.set_title(title, color="#22c55e" if done else fg, fontsize=12, pad=10)
        axes.set_xticks(range(size))
        axes.set_yticks(range(size))
        axes.tick_params(colors=panel, labelsize=7)
        for spine in axes.spines.values():
            spine.set_color(panel)

    images = []
    for index in range(len(steps)):
        frame(index)
        buffer = io.BytesIO()
        figure.savefig(buffer, format="png", facecolor=bg, dpi=110)
        buffer.seek(0)
        images.append(Image.open(buffer).convert("RGB"))
    plt.close(figure)
    durations = [700] * (len(images) - 1) + [2600]  # hold the settled frame
    images[0].save(
        out, save_all=True, append_images=images[1:], duration=durations, loop=0, optimize=True
    )
    print(f"wrote {out} ({len(images)} frames, {role} vs {opponent})")


def main() -> None:
    """CLI: --log <audited jsonl> --out <gif> [--config config]."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--config", default=ROOT / "config", type=Path)
    args = parser.parse_args()
    private = tomllib.loads((args.config / "game.toml").read_text(encoding="utf-8"))
    agreement = next(e for e in read_events(args.log) if e["event"] == "agreement_received")
    render(args.log, args.out, agreement["raw"]["terms"]["board_size"], private["gui"])


if __name__ == "__main__":
    main()

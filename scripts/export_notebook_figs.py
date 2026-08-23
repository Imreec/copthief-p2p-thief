"""Extract the committed notebook's rendered figures into assets/ (M8-1 README).

The M5-7 notebook is committed WITH outputs (renders-clean pin in CI), so its
figures are already evidence; this script only lifts the embedded PNGs out of
`notebooks/results_analysis.ipynb` so the README can embed them as images.
Re-run after re-executing the notebook; never hand-edit the extracted files.
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTEBOOK = ROOT / "notebooks" / "results_analysis.ipynb"
# Figure-bearing code cells, in notebook order (this repo's notebook; override the
# names on the command line where the sibling's notebook carries different figures).
NAMES = ["m5-ga-curve.png", "m5-weight-sensitivity.png"]


def extract(out_dir: Path, names: list[str]) -> list[Path]:
    """Write every image/png output of the notebook to out_dir (Input: target
    directory + one filename per figure, notebook order; Output: written paths)."""
    cells = json.loads(NOTEBOOK.read_text(encoding="utf-8"))["cells"]
    pngs = [
        output["data"]["image/png"]
        for cell in cells
        if cell["cell_type"] == "code"
        for output in cell.get("outputs", [])
        if "image/png" in output.get("data", {})
    ]
    if len(pngs) != len(names):
        msg = f"expected {len(names)} figures in the notebook, found {len(pngs)}"
        raise SystemExit(msg)
    written = []
    for name, payload in zip(names, pngs, strict=True):
        target = out_dir / name
        target.write_bytes(base64.b64decode(payload))
        written.append(target)
        print(f"wrote {target}")
    return written


if __name__ == "__main__":
    out = ROOT / "assets" if len(sys.argv) < 2 else Path(sys.argv[1])
    extract(out, sys.argv[2:] or NAMES)

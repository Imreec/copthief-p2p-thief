"""Derive a sparring-host config from the committed one (M7-1).

Why a script and not a committed second config directory: the signed constitution must
stay byte-identical (it is hashed into `config_sha256` and the terms signature), and a
hand-maintained copy drifts the moment either file is touched. So the constitution,
limits and locked models are copied VERBATIM, and exactly two things change in the
private TOML:

* every `[strategy.<role>]` table is dropped, so each brain falls back to its own
  canonical DEFAULT_OPTIONS — the generic brain (CLAUDE.md §9: tuned weights never
  deploy to a standing host);
* `[email]` is forced to the resting posture: disabled, no recipient (ADR-0008).

The result is loaded and put through `shared.sparring.assert_sparring_safe` before it is
written, so this script cannot emit a config the CLI would refuse to play.

Usage: uv run python scripts/make_sparring_config.py [--source config] [--out config-sparring]
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from copthief_core.shared.config import load_all  # noqa: E402
from copthief_core.shared.sparring import SparringUnsafeError, assert_sparring_safe  # noqa: E402

# Everything the peer loads is copied byte-for-byte; these are left behind on purpose.
# They are tuning outputs and dev artifacts (GA weights, arena rosters and their
# `brain_options`, the balance sim, the self-grade), no part of playing a game — and
# `ga_weights.json` / `arena*.json` carry the very numbers that may not deploy to a
# standing host. A sparring config has no business holding them even unread.
TUNING_ARTIFACTS = frozenset(
    {
        "ga.json",
        "ga_weights.json",
        "arena.json",
        "arena_champion.json",
        "balance.json",
        "self_grade.json",
    }
)
_SECTION = re.compile(r"^\[(?P<name>[^\]]+)\]\s*$")


def strip_tuned_tables(toml_text: str) -> str:
    """Drop every `[strategy.<role>]` sub-table (Input: game.toml text; Output: the same
    text with the tuned weight tables removed, comments and all)."""
    kept: list[str] = []
    skipping = False
    for line in toml_text.splitlines(keepends=True):
        header = _SECTION.match(line.strip())
        if header is not None:
            name = header.group("name")
            skipping = name.startswith("strategy.")
            if skipping:
                # Drop the comment block that introduces the table as well: it walks
                # backwards over the lines already kept.
                while kept and (kept[-1].lstrip().startswith("#") or not kept[-1].strip()):
                    kept.pop()
        if not skipping:
            kept.append(line)
    return "".join(kept)


def rest_email(toml_text: str) -> str:
    """Force `[email]` to the resting posture (disabled, no recipient)."""
    out: list[str] = []
    in_email = False
    for line in toml_text.splitlines(keepends=True):
        header = _SECTION.match(line.strip())
        if header is not None:
            in_email = header.group("name") == "email"
        if in_email and line.strip().startswith("enabled"):
            out.append("enabled = false\n")
        elif in_email and line.strip().startswith("recipient"):
            out.append("recipient = []\n")
        else:
            out.append(line)
    return "".join(out)


def derive(source: Path, out: Path) -> Path:
    """Write a sparring config derived from `source` (Output: the directory written;
    Raises: SparringUnsafeError if the result would break a standing rule)."""
    out.mkdir(parents=True, exist_ok=True)
    for candidate in sorted(source.iterdir()):
        if not candidate.is_file() or candidate.name == "game.toml":
            continue
        if candidate.name in TUNING_ARTIFACTS:
            continue
        shutil.copyfile(candidate, out / candidate.name)  # signed bytes, untouched
    text = (source / "game.toml").read_text(encoding="utf-8")
    (out / "game.toml").write_text(rest_email(strip_tuned_tables(text)), encoding="utf-8")
    _, private, _ = load_all(out, counted=False)
    assert_sparring_safe(private)  # cannot emit what the CLI would refuse
    return out


def main() -> int:
    """Derive the sparring config; print what changed."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("config"))
    parser.add_argument("--out", type=Path, default=Path("config-sparring"))
    args = parser.parse_args()
    try:
        written = derive(args.source, args.out)
    except SparringUnsafeError as error:
        print(f"FAIL: {error}")
        return 1
    print(f"OK: sparring config written to {written} (generic brain, no mail).")
    print(
        f"     play it with: uv run copthief run peer --role <role> --config {written} --sparring"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

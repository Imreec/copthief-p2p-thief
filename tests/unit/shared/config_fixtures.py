"""Config-tree fixtures shared by the loader suites.

Extracted at M7-7 so the budget-reconciliation tests clone a real config tree with the
same helper `test_config` uses, instead of copying it (CLAUDE.md §1 #11).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

CONFIG_DIR = Path("config")
CONFIG_FILES = (
    "game.json",
    "game.toml",
    "rate_limits.json",
    "app_f_table.json",
    "locked_models.json",
)


def copy_config(tmp_path: Path, **json_edits: object) -> Path:
    """Clone the shipped config/ into tmp_path, optionally editing game.json sections.

    Input: a tmp dir plus `section__param=value` edits. Output: the clone's path.
    """
    clone = tmp_path / "config"
    clone.mkdir(exist_ok=True)
    for name in CONFIG_FILES:
        clone.joinpath(name).write_bytes(CONFIG_DIR.joinpath(name).read_bytes())
    if json_edits:
        raw = json.loads(clone.joinpath("game.json").read_text(encoding="utf-8"))
        for dotted, value in json_edits.items():
            section, _, param = dotted.partition("__")
            raw[section][param] = value
        clone.joinpath("game.json").write_text(json.dumps(raw), encoding="utf-8")
    return clone


def set_toml_number(clone: Path, key: str, value: float) -> None:
    """Rewrite one bare `key = <number>` line in a cloned game.toml (Input: the clone
    dir, the private key, its new value; Output: none — the file is rewritten in place).
    """
    path = clone / "game.toml"
    text = path.read_text(encoding="utf-8")
    patched, hits = re.subn(rf"(?m)^{re.escape(key)} = .*$", f"{key} = {value}", text)
    if hits != 1:
        raise AssertionError(f"{key}: expected exactly one assignment, patched {hits}")
    path.write_text(patched, encoding="utf-8")

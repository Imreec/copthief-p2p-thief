"""Per-model strategy weights (M7-15): `[strategy.<role>.<scent_model>]` overlays.

The M7-14 gate comparison proved the tuned vectors are PHYSICS-SPECIFIC (the book-v1
winner loses the reference table and vice versa), so deployment must follow the
selected model. These pin the mechanism role-blind and value-blind (gotcha #9: this
file is mirrored, and the two repos ship different base tables): a sub-table named
after a scent model overlays the base ONLY when that model is the selected one, and
configs without sub-tables resolve to the base exactly.
"""

import re
from pathlib import Path

from copthief_core.shared.private_config import load_private_settings

SHIPPED = (Path("config") / "game.toml").read_text(encoding="utf-8")
SENTINEL_TABLES = """
[strategy.police.test_model_x]
w_sentinel = 9.9

[strategy.thief.test_model_x]
w_sentinel = 8.8
"""


def _load(tmp_path: Path, toml_text: str) -> object:
    (tmp_path / "locked_models.json").write_bytes(
        (Path("config") / "locked_models.json").read_bytes()
    )
    path = tmp_path / "game.toml"
    path.write_text(toml_text, encoding="utf-8")
    return load_private_settings(path)


def _select_model(text: str, name: str) -> str:
    """Point the [scent] model line at `name` (the only bare `model =` line)."""
    replaced, count = re.subn(r'(?m)^model = ".*"$', f'model = "{name}"', text)
    assert count == 1
    return replaced


def test_a_per_model_sub_table_overlays_only_under_its_model(tmp_path: Path) -> None:
    text = _select_model(SHIPPED + SENTINEL_TABLES, "test_model_x")
    private = _load(tmp_path, text)
    police = private.strategy_options("police")
    thief = private.strategy_options("thief")
    assert police == {**private.police_options, "w_sentinel": 9.9}
    assert thief == {**private.thief_options, "w_sentinel": 8.8}


def test_the_sub_table_is_inert_under_a_different_model(tmp_path: Path) -> None:
    private = _load(tmp_path, SHIPPED + SENTINEL_TABLES)  # shipped model selected
    assert "w_sentinel" not in private.strategy_options("police")
    assert "w_sentinel" not in private.strategy_options("thief")
    assert private.strategy_options("police") == {
        **private.police_options,
        **private.police_model_options.get(private.scent_model, {}),
    }


def test_a_config_without_sub_tables_resolves_to_the_base_exactly(tmp_path: Path) -> None:
    """Strip every per-model sub-table from the shipped file: resolution == base."""
    stripped = re.sub(r"(?ms)^\[strategy\.(police|thief)\.[^\]]+\].*?(?=^\[|\Z)", "", SHIPPED)
    private = _load(tmp_path, stripped)
    assert private.police_model_options == {}
    assert private.thief_model_options == {}
    assert private.strategy_options("police") == private.police_options
    assert private.strategy_options("thief") == private.thief_options

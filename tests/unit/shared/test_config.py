"""Config loader (PRD_engine §5; App B): typed constitution, JSON-wins rule, versions, precedence."""

import json
from pathlib import Path

import pytest

from copthief_core.domain.scoring import ScoringTable
from copthief_core.shared.config import ConfigError, load_all

CONFIG_DIR = Path("config")


def _copy_config(tmp_path: Path, **json_edits: object) -> Path:
    """Clone the shipped config/ into tmp_path, optionally editing game.json sections."""
    clone = tmp_path / "config"
    clone.mkdir()
    for name in (
        "game.json",
        "game.toml",
        "rate_limits.json",
        "app_f_table.json",
        "locked_models.json",
    ):
        clone.joinpath(name).write_bytes(CONFIG_DIR.joinpath(name).read_bytes())
    if json_edits:
        raw = json.loads(clone.joinpath("game.json").read_text(encoding="utf-8"))
        for dotted, value in json_edits.items():
            section, _, param = dotted.partition("__")
            raw[section][param] = value
        clone.joinpath("game.json").write_text(json.dumps(raw), encoding="utf-8")
    return clone


def test_shipped_config_loads_into_a_typed_constitution() -> None:
    constitution, private, limits = load_all(CONFIG_DIR, counted=False)
    assert isinstance(constitution.board.grid_size, int)
    assert constitution.movement.move_set == ("N", "S", "E", "W", "STAY")
    assert isinstance(constitution.scoring, ScoringTable)
    assert isinstance(constitution.pheromones.decay, float)
    assert private.version == "1.00"
    assert limits.requests_per_minute >= constitution.gatekeeper.requests_per_minute


def test_gui_section_loads_typed_display_knobs() -> None:
    # PRD_gui_replay §7: every quantitative render value is config-owned ([gui] is
    # private, display-only, never negotiated).
    _constitution, private, _limits = load_all(CONFIG_DIR, counted=False)
    assert private.gui.refresh_ms > 0
    assert private.gui.cell_px > 0
    assert private.gui.png_dpi > 0
    assert private.gui.font_size > 0
    assert private.gui.font_family
    colors = (
        private.gui.heat_low,
        private.gui.heat_high,
        private.gui.theme_bg,
        private.gui.theme_panel,
        private.gui.theme_fg,
        private.gui.accent,
    )
    for color in colors:
        assert color.startswith("#")
        assert len(color) == 7


def test_constitution_builds_the_board_from_the_signed_axis_contract() -> None:
    constitution, _, _ = load_all(CONFIG_DIR, counted=False)
    board = constitution.board.make_board()
    assert board.grid_size == constitution.board.grid_size
    assert board.axis_origin_corner == constitution.board.axis_origin_corner
    assert board.barriers == frozenset()


def test_guard_violation_refuses_the_load_loudly(tmp_path: Path) -> None:
    clone = _copy_config(tmp_path, scoring__capture_cop=25)
    with pytest.raises(ConfigError, match="scoring.capture_cop"):
        load_all(clone, counted=False)


def test_counted_flag_arms_the_num_games_rule(tmp_path: Path) -> None:
    clone = _copy_config(tmp_path)
    with pytest.raises(ConfigError, match="num_games"):
        load_all(clone, counted=True)


def test_private_toml_can_never_override_a_signed_term(tmp_path: Path) -> None:
    clone = _copy_config(tmp_path)
    toml = clone / "game.toml"
    toml.write_text(toml.read_text(encoding="utf-8") + "\ngrid_size = 99\n", encoding="utf-8")
    constitution, _, _ = load_all(clone, counted=False)
    assert constitution.board.grid_size != 99  # JSON overlays TOML on shared keys (App B)


def test_malformed_private_version_is_refused(tmp_path: Path) -> None:
    clone = _copy_config(tmp_path)
    toml = clone / "game.toml"
    toml.write_text(
        toml.read_text(encoding="utf-8").replace('version = "1.00"', 'version = "1.0"'),
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="version"):
        load_all(clone, counted=False)


def test_min_center_intensity_reads_the_reference_schema_key(tmp_path: Path) -> None:
    # M2 finding F4 (oracle sha 960499fd): the reference's game.json schema 1.3 carries
    # the emission gate as pheromones.pheromone_min_center_intensity — a signed shared
    # key, not a reference-code-only default. The loader must read that exact key.
    clone = _copy_config(tmp_path, pheromones__pheromone_min_center_intensity=0.7)
    constitution, _, _ = load_all(clone, counted=False)
    assert constitution.pheromones.min_center_intensity == 0.7


def test_min_center_intensity_defaults_when_the_signed_file_omits_it(tmp_path: Path) -> None:
    clone = _copy_config(tmp_path)  # shipped game.json omits the key
    constitution, _, _ = load_all(clone, counted=False)
    assert constitution.pheromones.min_center_intensity == 0.5


def test_rate_limits_below_a_signed_minimum_are_refused(tmp_path: Path) -> None:
    clone = _copy_config(tmp_path)
    limits_path = clone / "rate_limits.json"
    raw = json.loads(limits_path.read_text(encoding="utf-8"))
    raw["requests_per_minute"] = 10
    limits_path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ConfigError, match="requests_per_minute"):
        load_all(clone, counted=False)


def test_rate_limits_above_the_signed_minimums_are_accepted(tmp_path: Path) -> None:
    clone = _copy_config(tmp_path)
    limits_path = clone / "rate_limits.json"
    raw = json.loads(limits_path.read_text(encoding="utf-8"))
    raw["queue_depth"] = 500
    limits_path.write_text(json.dumps(raw), encoding="utf-8")
    _, _, limits = load_all(clone, counted=False)
    assert limits.queue_depth == 500

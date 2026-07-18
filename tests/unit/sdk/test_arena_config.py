"""Arena config loader (M5-2; PRD_police_brain §4): rosters/seeds/options from config.

The arena's quantitative knobs moved out of mirrored code into per-repo
`config/arena.json` — required by the role split (each repo's roster names its own
role package) and by CLAUDE.md constraint #5. The loader validates the version,
normalizes dotted-spec entries, and refuses malformed files loudly.
"""

import json
from pathlib import Path

import pytest

from copthief_core.sdk.arena_config import ArenaConfig, load_arena_config
from copthief_core.shared.private_config import ConfigError


def test_shipped_arena_config_loads_and_names_both_rosters() -> None:
    config = load_arena_config(Path("config") / "arena.json")
    assert isinstance(config, ArenaConfig)
    assert [e.name for e in config.police_roster]  # non-empty
    assert [e.name for e in config.thief_roster]
    assert config.seeds
    assert config.scenario_min_separation >= 1
    assert config.evidence_out.endswith(".md")


def test_dotted_spec_entries_normalize_to_alias_plus_spec(tmp_path: Path) -> None:
    raw = json.loads((Path("config") / "arena.json").read_text(encoding="utf-8"))
    raw["police_roster"] = [
        "random",
        {"name": "police-brain", "spec": "copthief_police.brain:PoliceBrain"},
    ]
    path = tmp_path / "arena.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    config = load_arena_config(path)
    entry = config.police_roster[1]
    assert entry.name == "police-brain"
    assert entry.spec == "copthief_police.brain:PoliceBrain"
    plain = config.police_roster[0]
    assert plain.name == plain.spec == "random"


def test_brain_options_reach_the_named_brain_only() -> None:
    config = load_arena_config(Path("config") / "arena.json")
    assert config.options_for("ref-police")  # the attributed coin-flip rate lives here
    assert config.options_for("random") == {}


def test_malformed_version_is_refused_loudly(tmp_path: Path) -> None:
    raw = json.loads((Path("config") / "arena.json").read_text(encoding="utf-8"))
    raw["version"] = "one"
    path = tmp_path / "arena.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ConfigError):
        load_arena_config(path)

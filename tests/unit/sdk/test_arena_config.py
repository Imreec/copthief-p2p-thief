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


def test_scent_model_and_roster_feeds_parse_with_safe_defaults(tmp_path: Path) -> None:
    """M7-14 doors: an arena config may select the physics for the WHOLE run and a
    per-thief-entry information feed; both default to the shipped behavior (reference
    physics, hidden feed) so the existing arena.json is untouched by the feature."""
    raw = json.loads((Path("config") / "arena.json").read_text(encoding="utf-8"))
    raw["scent_model"] = "multiplicative_book_v1"
    raw["thief_roster"] = [
        "ref-thief",
        {"name": "evader-lag1", "spec": "belief-evader", "feed": "truth-lag1"},
    ]
    path = tmp_path / "arena.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    config = load_arena_config(path)
    assert config.scent_model == "multiplicative_book_v1"
    assert config.thief_roster[0].feed is None
    assert config.thief_roster[1].feed == "truth-lag1"
    shipped = load_arena_config(Path("config") / "arena.json")
    assert shipped.scent_model is None


def test_police_claim_threshold_parses_and_defaults_to_unmodelled(tmp_path: Path) -> None:
    """M7-19: a police roster entry may carry a claim threshold, switching the claim
    channel on for that cop. Absent, claims stay UNMODELLED — the historical physics
    every committed arena table was measured under, so no existing config shifts."""
    raw = json.loads((Path("config") / "arena.json").read_text(encoding="utf-8"))
    raw["police_roster"] = [
        "ref-police",
        {"name": "quiet-cop", "spec": "ref-police", "claim_threshold": 0.25},
        {"name": "loud-cop", "spec": "ref-police", "claim_threshold": 0.0},
    ]
    path = tmp_path / "arena.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    config = load_arena_config(path)
    assert config.police_roster[0].claim_threshold is None
    assert config.police_roster[1].claim_threshold == 0.25
    assert config.police_roster[2].claim_threshold == 0.0  # modelled, and always claims
    assert config.claim_threshold_for("quiet-cop") == 0.25
    assert config.claim_threshold_for("ref-police") is None
    # The claim feed is PER THIEF ENTRY: the sweep's whole point is a mixture where some
    # opponents read our claims and others ignore them.
    raw["thief_roster"] = [
        "ref-thief",
        {"name": "claim-reader", "spec": "belief-evader", "claim_feed": "truth"},
    ]
    path.write_text(json.dumps(raw), encoding="utf-8")
    mixed = load_arena_config(path)
    assert mixed.thief_roster[0].claim_feed is None
    assert mixed.thief_roster[1].claim_feed == "truth"
    shipped = load_arena_config(Path("config") / "arena.json")
    assert all(entry.claim_threshold is None for entry in shipped.police_roster)


def test_champion_pin_defaults_to_the_shipped_gate_and_can_opt_out(tmp_path: Path) -> None:
    """Measurement configs (M7-14) skip the champion gate by pinning null; the
    shipped arena.json keeps the CI gate without naming it."""
    shipped = load_arena_config(Path("config") / "arena.json")
    assert shipped.champion_pin == "config/arena_champion.json"
    raw = json.loads((Path("config") / "arena.json").read_text(encoding="utf-8"))
    raw["champion_pin"] = None
    path = tmp_path / "arena.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    assert load_arena_config(path).champion_pin is None

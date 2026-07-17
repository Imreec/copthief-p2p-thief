"""Terms extraction (PRD_crypto §5): reference key names, kit-pinned shape, config-sourced."""

from pathlib import Path

from copthief_core.domain.terms import terms_from_config
from copthief_core.shared.config import load_all

CONSTITUTION, _PRIVATE, _LIMITS = load_all(Path("config"), counted=False)

# The kit's terms_signature.json vector key set — our M1 pin, byte-verified vs the live
# reference at M2-2 (PRD_crypto §8.3).
KIT_TERMS_KEYS = {
    "board_size",
    "smell_grid_size",
    "decay_per_step",
    "emit_intensity",
    "min_center_intensity",
    "max_steps",
    "barriers_max",
    "setting",
    "hint_max_words",
    "axis_origin_corner",
    "axis_start_index",
    "thief_start",
    "cop_start",
    "num_games",
}


def test_terms_carry_exactly_the_kit_pinned_key_set() -> None:
    assert set(terms_from_config(CONSTITUTION)) == KIT_TERMS_KEYS


def test_terms_values_map_from_the_signed_constitution() -> None:
    terms = terms_from_config(CONSTITUTION)
    assert terms["board_size"] == CONSTITUTION.board.grid_size
    assert terms["smell_grid_size"] == CONSTITUTION.pheromones.grid_size
    assert terms["decay_per_step"] == CONSTITUTION.pheromones.decay
    assert terms["emit_intensity"] == CONSTITUTION.pheromones.center_intensity
    assert terms["max_steps"] == CONSTITUTION.movement.survival_threshold
    assert terms["barriers_max"] == CONSTITUTION.movement.max_barriers
    assert terms["setting"] == CONSTITUTION.world.map_area
    assert terms["num_games"] == CONSTITUTION.league.num_games


def test_max_steps_maps_from_survival_threshold_not_max_moves() -> None:
    # M2 finding F3 (oracle sha 960499fd): the reference's _translate_shared maps its
    # terms' max_steps from movement_and_barriers.survival_threshold — NOT max_moves.
    # The shipped configs hold both at the same value, which is exactly why only a
    # discriminating constitution can pin the provenance.
    from dataclasses import replace

    skewed = replace(
        CONSTITUTION, movement=replace(CONSTITUTION.movement, max_moves=40, survival_threshold=35)
    )
    assert terms_from_config(skewed)["max_steps"] == 35


def test_min_center_intensity_defaults_from_the_app_f_table_when_absent() -> None:
    # Reference-only parameter (kit §5): not in the shipped game.json, so the App F
    # transcription's default must flow through the loader (PRD_crypto §8.2).
    assert CONSTITUTION.pheromones.min_center_intensity == 0.5
    assert terms_from_config(CONSTITUTION)["min_center_intensity"] == 0.5


def test_terms_starts_stay_json_array_shaped() -> None:
    terms = terms_from_config(CONSTITUTION)
    assert list(terms["thief_start"]) == list(CONSTITUTION.board.thief_start)
    assert list(terms["cop_start"]) == list(CONSTITUTION.board.cop_start)

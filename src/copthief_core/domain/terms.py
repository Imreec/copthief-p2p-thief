"""Terms extraction (kit SPEC §4; PRD_crypto §5): the signed subset both peers must match.

The terms dict is a MAPPED extraction from the constitution — the kit's vectors pin the
REFERENCE'S key names (`board_size`, `barriers_max`, `setting`, …), which deliberately
differ from the `game.json` schema names. This mapping is our M1 pin of the reference's
`terms_from_config`; M2-2 byte-verifies it against the live reference peer — a mismatch
there fails the negotiate gate visibly (PRD_crypto §8.3).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # annotation-only: domain stays free of runtime shared imports
    from copthief_core.shared.config_model import Constitution


def terms_from_config(constitution: Constitution) -> dict[str, object]:
    """The agreement-signature / game_uid preimage, in the kit-pinned key set.

    Input: the guard-validated constitution. Output: the terms dict whose canonical
    bytes both peers sign (`terms_signature`) and derive `game_uid` from. Starts stay
    sequence-shaped (they canonicalize to JSON arrays, as in the kit vectors).
    """
    return {
        "board_size": constitution.board.grid_size,
        "smell_grid_size": constitution.pheromones.grid_size,
        "decay_per_step": constitution.pheromones.decay,
        "emit_intensity": constitution.pheromones.center_intensity,
        "min_center_intensity": constitution.pheromones.min_center_intensity,
        "max_steps": constitution.movement.max_moves,
        "barriers_max": constitution.movement.max_barriers,
        "setting": constitution.world.map_area,
        "hint_max_words": constitution.world.hint_max_words,
        "axis_origin_corner": constitution.board.axis_origin_corner,
        "axis_start_index": constitution.board.axis_start_index,
        "thief_start": constitution.board.thief_start,
        "cop_start": constitution.board.cop_start,
        "num_games": constitution.league.num_games,
    }

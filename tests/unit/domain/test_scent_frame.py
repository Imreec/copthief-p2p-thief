"""The in-play frame validity check (PRD_scent §10; M7-23).

Across two consecutive frames from one sender the whole history cancels: the current
frame must be ONE advance of the previous one for SOME emitter cell. A frame no cell
can explain is provably not the output of a rules-following peer. The validator's
surface is verdict-only — the matched candidate never leaves it (§10.1 firewall: the
same arithmetic localizes, and this check must not become that).

Honest traffic is generated through the shipped ScentField/model path — the exact
code the sender runs — so the false-positive property tests the real construction.
"""

from pathlib import Path

from copthief_core.domain.scent import ScentField
from copthief_core.domain.scent_frame import __all__ as surface
from copthief_core.domain.scent_frame import frame_explained
from copthief_core.domain.scent_models import make_scent_model
from copthief_core.shared.config import load_all
from copthief_core.shared.locked_models import SCENT_MODEL

CONSTITUTION, PRIVATE, _LIMITS = load_all(Path("config"), counted=False)
SIZE = CONSTITUTION.board.grid_size
ORIGIN = CONSTITUTION.board.axis_start_index
INTENSITY = CONSTITUTION.pheromones.center_intensity

# A deterministic walk that exercises moves, direction changes, edge/corner clipping
# and dwells (STAY ≡ a barrier turn to the validator: the emitter cell is unchanged).
_DELTAS = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "W": (0, -1), "STAY": (0, 0)}
_WALK = ["E", "E", "S", "STAY", "S", "W", "STAY", "STAY", "N", "W", "W", "STAY"]
_DWELL = ["STAY"] * 12  # saturated-camp regime under the book model's clamp


def _model(name: str):  # noqa: ANN202 - test helper
    doc = PRIVATE.locked_models.doc(SCENT_MODEL, name)
    return make_scent_model(name, params=doc["params"])


def _snapshots(model_name: str, moves: list[str]) -> list[dict[str, float]]:
    """The transmitted frames an honest sender produces along `moves` (from empty)."""
    field = ScentField(board_size=SIZE, origin=ORIGIN, model=_model(model_name))
    row, col = ORIGIN + SIZE // 2, ORIGIN + SIZE // 2
    frames = []
    for move in moves:
        d_row, d_col = _DELTAS[move]
        row = min(max(row + d_row, ORIGIN), ORIGIN + SIZE - 1)
        col = min(max(col + d_col, ORIGIN), ORIGIN + SIZE - 1)
        field.advance((row, col), INTENSITY)
        frames.append(field.snapshot())
    return frames


def _explained(prev: dict[str, float], now: dict[str, float], model_name: str) -> bool:
    return frame_explained(
        prev,
        now,
        model=_model(model_name),
        board_size=SIZE,
        origin=ORIGIN,
        intensity=INTENSITY,
        tolerance=PRIVATE.scent_physics_tolerance,
    )


def test_honest_walk_never_refused_reference_model() -> None:
    """The false-positive property (§10.4): a false refusal is worse than no check."""
    frames = _snapshots("subtractive_chebyshev_v1", _WALK)
    assert _explained({}, frames[0], "subtractive_chebyshev_v1")  # step 1 vs empty
    for prev, now in zip(frames, frames[1:], strict=False):
        assert _explained(prev, now, "subtractive_chebyshev_v1")


def test_honest_walk_never_refused_book_model() -> None:
    frames = _snapshots("multiplicative_book_v1", _WALK)
    assert _explained({}, frames[0], "multiplicative_book_v1")
    for prev, now in zip(frames, frames[1:], strict=False):
        assert _explained(prev, now, "multiplicative_book_v1")


def test_saturated_dwell_never_refused_book_model() -> None:
    """The clamp does not break the relation: a 12-turn camp stays explainable."""
    frames = _snapshots("multiplicative_book_v1", _DWELL)
    for prev, now in zip(frames, frames[1:], strict=False):
        assert _explained(prev, now, "multiplicative_book_v1")


def test_perturbed_cell_refuses() -> None:
    """A decoy: one cell nudged beyond tolerance has no consistent emitter."""
    frames = _snapshots("subtractive_chebyshev_v1", _WALK)
    forged = dict(frames[3])
    key = next(iter(forged))
    forged[key] = round(forged[key] + 0.05, 3)
    assert not _explained(frames[2], forged, "subtractive_chebyshev_v1")


def test_stale_frame_refuses() -> None:
    """A peer restarting mid-series: frame t+2 is not ONE advance of frame t."""
    frames = _snapshots("subtractive_chebyshev_v1", _WALK)
    assert not _explained(frames[2], frames[5], "subtractive_chebyshev_v1")


def test_forged_first_frame_refuses() -> None:
    """Step 1 pairs against the empty initial field, so even it is checkable: a grid
    that is not one fresh deposit (here: two fresh centres) has no emitter."""
    frames = _snapshots("subtractive_chebyshev_v1", ["E"])
    forged = dict(frames[0])
    far_row, far_col = ORIGIN + SIZE - 1, ORIGIN + SIZE - 1
    forged[f"{far_row},{far_col}"] = max(forged.values())
    assert not _explained({}, forged, "subtractive_chebyshev_v1")


def test_surface_is_verdict_only() -> None:
    """§10.1 firewall pin: the module exposes the boolean and nothing that could
    carry the matched candidate cell out of it."""
    assert surface == ["frame_explained"]
    frames = _snapshots("subtractive_chebyshev_v1", ["E", "S"])
    verdict = _explained(frames[0], frames[1], "subtractive_chebyshev_v1")
    assert verdict is True  # a bool, not a cell-bearing structure

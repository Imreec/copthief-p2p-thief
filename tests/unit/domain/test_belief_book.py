"""Book-model belief observation — kernel match, not age inversion (M7-14).

The M3-8 measurement isolated two causes of the book model's 17% argmax hit-rate:
kernel saturation (the registered model's own arithmetic — untouchable) and OUR
voucher heuristic reading intensity as AGE (a fresh ring-1 cell inverts to "age 4"
and whispers over a huge ball). The evidence doc's own prescription: a filter built
for this model treats the kernel as a SPATIAL LIKELIHOOD. These tests pin that
observation model: a fresh kernel's shape identifies its center, a flat saturated
camp blob is penalized for its missing ring structure, and the measured hit-rate
moves from ~0.17 to something a pursuit can actually use.
"""

from pathlib import Path

from copthief_core.domain.belief_observation import kernel_match_score
from copthief_core.shared.config import load_all
from copthief_core.shared.locked_models import build_scent_model
from copthief_core.strategy.belief_eval import run_belief_trial

CONSTITUTION, PRIVATE, _ = load_all(Path("config"), counted=False)
BOOK = build_scent_model(PRIVATE.locked_models, "multiplicative_book_v1", CONSTITUTION.pheromones)
KERNEL = BOOK.spatial_kernel()
BOARD = CONSTITUTION.board.make_board()


def _fresh_kernel_at(center: tuple[int, int]) -> dict[tuple[int, int], float]:
    assert KERNEL is not None
    half = len(KERNEL) // 2
    obs = {}
    for d_row in range(-half, half + 1):
        for d_col in range(-half, half + 1):
            cell = (center[0] + d_row, center[1] + d_col)
            if BOARD.in_bounds(cell) and KERNEL[half + d_row][half + d_col] > 0.0:
                obs[cell] = KERNEL[half + d_row][half + d_col]
    return obs


def test_an_exact_fresh_kernel_scores_perfectly_at_its_center() -> None:
    obs = _fresh_kernel_at((3, 3))
    assert KERNEL is not None
    assert kernel_match_score(obs, (3, 3), KERNEL, BOARD) == 1.0
    assert kernel_match_score(obs, (3, 4), KERNEL, BOARD) < 1.0


def test_a_flat_saturated_camp_blob_scores_below_a_true_kernel() -> None:
    """The g02 signature: a camper pins its neighbourhood at the 0.9 ceiling. A flat
    blob has no ring structure, so the hypothesis at its center must score WORSE than
    the true kernel scores at its own center — the voucher heuristic said the
    opposite (every 0.9 cell reads age 0 and spikes)."""
    assert KERNEL is not None
    ceiling = max(max(row) for row in KERNEL)
    blob = {(4 + dr, 4 + dc): ceiling for dr in (-1, 0, 1) for dc in (-1, 0, 1)}
    kernel_score = kernel_match_score(_fresh_kernel_at((3, 3)), (3, 3), KERNEL, BOARD)
    blob_score = kernel_match_score(blob, (4, 4), KERNEL, BOARD)
    assert blob_score < kernel_score


def test_the_measured_book_hit_rate_leaves_the_17_percent_floor() -> None:
    """The deliverable metric (same instrument as docs/evidence/m3-belief-eval.md):
    under the book model the filter's argmax must now find the true cell on at least
    half the steps, averaged over the first three evidence seeds — the age-voucher
    filter measured 0.17."""
    rates = []
    for seed in (1, 2, 3):
        trial = run_belief_trial(
            CONSTITUTION,
            smell_trust=PRIVATE.smell_trust_weight,
            seed=seed,
            steps=CONSTITUTION.movement.survival_threshold,
            scent_model=build_scent_model(
                PRIVATE.locked_models, "multiplicative_book_v1", CONSTITUTION.pheromones
            ),
        )
        rates.append(trial.filter_hit_rate)
    assert sum(rates) / len(rates) >= 0.5

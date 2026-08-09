"""Seeded tie-break variance, evader half (M9-5) — the determinism kill.

The counted 30–90 replayed byte-identical games three times: signed starts +
brains whose tie-breaks never consumed their seed = an opponent replays a
proven kill script after game one. This mirrored file pins the CORE side (the
doctrine evader's seeded exact-tie shuffle); the cop-side tie_epsilon pins
import `copthief_police` and live in tests/role/test_police_seed_variance.py —
role tests stay per-repo, which the M9 sync into the thief repo enforced the
hard way.
"""

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import Board
from copthief_core.strategy.brains import Observation
from copthief_core.strategy.doctrine_evader import DoctrineEvaderBrain

MOVE_SET = ("N", "S", "E", "W", "STAY")


def make_board() -> Board:
    return Board(grid_size=7, axis_origin_corner="top-left", axis_start_index=0)


def make_belief(board: Board, cell: tuple[int, int]) -> BeliefFilter:
    return BeliefFilter(
        board=board,
        move_set=MOVE_SET,
        start=cell,
        center_intensity=0.9,
        decay=0.1,
        smell_trust=0.0,
        hint_trust=0.0,
    )


def make_observation(board: Board, position: tuple[int, int]) -> Observation:
    return Observation(
        board=board,
        position=position,
        move_set=MOVE_SET,
        role="thief",
        step=5,
        barriers_used=0,
        max_barriers=14,
        max_moves=35,
    )


def test_evader_exact_ties_vary_by_seed() -> None:
    """Symmetric flight (cop far, all destinations tuple-equal): the seeded
    shuffle resolves the tie differently across sub-game seeds."""
    board = make_board()

    def move_for(seed: int) -> str:
        belief = make_belief(board, (0, 0))
        brain = DoctrineEvaderBrain(seed=seed)
        return brain.pick_move(make_observation(board, (3, 3)), belief)

    assert len({move_for(seed) for seed in range(12)}) > 1


def test_evader_same_seed_is_reproducible() -> None:
    """Same (config, seed) = the same decision — replay evidence stays valid."""
    board = make_board()

    def move_for() -> str:
        belief = make_belief(board, (0, 0))
        brain = DoctrineEvaderBrain(seed=11)
        return brain.pick_move(make_observation(board, (3, 3)), belief)

    assert move_for() == move_for()

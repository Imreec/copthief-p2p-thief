"""BrainBase seam + baseline brains (TODO M3-5; PLAN §8).

The seam contract: `_pick_move(observation, belief) -> move`; the public
`pick_move` template method clamps every proposal to legality (never an illegal
move on the wire, never a stalled loop). Baselines: seeded random and
greedy-Manhattan over the belief argmax — deliberately simple, they are the
arena floor the M5 role brains must beat.
"""

import pytest

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import Board
from copthief_core.strategy.brains import (
    BrainBase,
    GreedyManhattanBrain,
    Observation,
    RandomBrain,
    make_brain,
)

MOVE_SET = ("N", "S", "E", "W", "STAY")


def make_board(barriers: frozenset = frozenset()) -> Board:  # type: ignore[type-arg]
    return Board(grid_size=7, axis_origin_corner="top-left", axis_start_index=0, barriers=barriers)


def make_belief(board: Board, opponent_at: tuple[int, int]) -> BeliefFilter:
    return BeliefFilter(
        board=board,
        move_set=MOVE_SET,
        start=opponent_at,
        center_intensity=0.9,
        decay=0.1,
        smell_trust=4.0,
        hint_trust=1.0,
    )


def observation(board: Board, position: tuple[int, int], role: str) -> Observation:
    return Observation(board=board, position=position, move_set=MOVE_SET, role=role, step=1)


class _StubbornBrain(BrainBase):
    """Always proposes the same move — exercises the legality clamp."""

    def __init__(self, move: str) -> None:
        super().__init__(seed=0)
        self._move = move

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        return self._move


def test_template_method_clamps_an_illegal_proposal_deterministically() -> None:
    board = make_board(barriers=frozenset({(2, 3)}))
    belief = make_belief(board, (0, 0))
    move = _StubbornBrain("N").pick_move(observation(board, (3, 3), "police"), belief)
    assert move == "E"  # N is blocked; the clamp falls to the first sorted legal move


def test_template_method_stays_when_nothing_is_legal() -> None:
    walls = frozenset({(0, 1), (1, 0), (0, 0)})  # own cell barriered too (pathological)
    board = make_board(barriers=walls)
    belief = make_belief(board, (6, 6))
    move = _StubbornBrain("N").pick_move(observation(board, (0, 0), "thief"), belief)
    assert move == "STAY"  # never stall, never crash — audit resolves the imprisonment


def test_random_brain_is_seed_reproducible_and_always_legal() -> None:
    board = make_board(barriers=frozenset({(2, 3), (3, 2)}))
    belief = make_belief(board, (0, 0))
    first = [
        RandomBrain(seed=7).pick_move(observation(board, (3, 3), "thief"), belief) for _ in range(1)
    ]
    again = [
        RandomBrain(seed=7).pick_move(observation(board, (3, 3), "thief"), belief) for _ in range(1)
    ]
    assert first == again
    brain = RandomBrain(seed=11)
    for _ in range(50):
        move = brain.pick_move(observation(board, (3, 3), "thief"), belief)
        assert move in {"S", "E", "STAY"}  # N and W are barriered


def test_greedy_police_closes_the_manhattan_distance_to_the_belief_argmax() -> None:
    board = make_board()
    belief = make_belief(board, (0, 6))  # the filter is certain: opponent at (0, 6)
    brain = GreedyManhattanBrain(seed=1)
    move = brain.pick_move(observation(board, (3, 3), "police"), belief)
    assert move in {"N", "E"}  # both close the distance; the choice is deterministic
    assert brain.pick_move(observation(board, (3, 3), "police"), belief) == move


def test_greedy_thief_grows_the_manhattan_distance_from_the_belief_argmax() -> None:
    board = make_board()
    belief = make_belief(board, (0, 0))  # cop believed at the origin corner
    move = GreedyManhattanBrain(seed=1).pick_move(observation(board, (3, 3), "thief"), belief)
    assert move in {"S", "E"}  # both flee the corner


def test_greedy_respects_barriers_via_the_clamp() -> None:
    board = make_board(barriers=frozenset({(2, 3), (3, 4)}))  # N and E blocked
    belief = make_belief(board, (0, 6))
    move = GreedyManhattanBrain(seed=1).pick_move(observation(board, (3, 3), "police"), belief)
    assert move in {"S", "W", "STAY"}


def test_observation_carries_the_signed_clock_with_inert_defaults() -> None:
    board = make_board()
    bare = observation(board, (3, 3), "thief")
    assert (bare.survival_threshold, bare.max_moves) == (0, 0)  # legacy callers unchanged
    timed = Observation(
        board=board,
        position=(3, 3),
        move_set=MOVE_SET,
        role="thief",
        step=1,
        survival_threshold=40,
        max_moves=60,
    )
    assert (timed.survival_threshold, timed.max_moves) == (40, 60)


def test_factory_builds_by_config_name_and_refuses_unknowns() -> None:
    assert isinstance(make_brain("random", seed=1), RandomBrain)
    assert isinstance(make_brain("greedy-manhattan", seed=1), GreedyManhattanBrain)
    with pytest.raises(ValueError, match="unknown brain"):
        make_brain("skynet", seed=1)


def test_belief_evader_is_a_core_brain_name() -> None:
    """The trap-aware evader must be reachable from arena/GA rosters by name in BOTH
    role repos (core registry, not a dotted role-package spec — M7-14)."""
    from copthief_core.strategy.brains import make_brain
    from copthief_core.strategy.evader_brains import BeliefEvaderBrain

    brain = make_brain("belief-evader", seed=3, options={"stay_penalty": 1.5})
    assert isinstance(brain, BeliefEvaderBrain)

"""uoh-sqak arena arm pins (M7-46) — ⚑ thief repo, opponent model only.

Pins the properties the arm exists to supply: it strangles reachable AREA (the term
their objective is dominated by), it obeys our barrier law, and it walls only when their
own objective prefers a wall to the step it would forgo. Since `d07b654` their cop obeys
the Barrier Law too, so the tempo divergence is gone and this arm matches their turn law;
the ONE remaining divergence — no endgame layer — is pinned below, so nobody later reads
a survival against this arm as a survival against them.
"""

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import Board
from copthief_core.domain.rules import is_legal_barrier
from copthief_core.strategy.brains import Observation
from copthief_thief.sqak_apex import APEX_DEFAULTS, SqakApexPoliceBrain

MOVE_SET = ("N", "S", "E", "W", "STAY")


def make_board(barriers: frozenset = frozenset()) -> Board:  # type: ignore[type-arg]
    return Board(grid_size=7, axis_origin_corner="top-left", axis_start_index=0, barriers=barriers)


def make_belief(board: Board, thief_at: tuple[int, int]) -> BeliefFilter:
    return BeliefFilter(
        board=board,
        move_set=MOVE_SET,
        start=thief_at,
        center_intensity=0.9,
        decay=0.1,
        smell_trust=4.0,
        hint_trust=0.0,
    )


def observation(
    board: Board, position: tuple[int, int], *, barriers_used: int = 0, step: int = 1
) -> Observation:
    return Observation(
        board=board,
        position=position,
        move_set=MOVE_SET,
        role="police",
        step=step,
        barriers_used=barriers_used,
        max_barriers=14,
        survival_threshold=35,
        max_moves=35,
    )


def test_the_fielded_weights_are_the_ones_they_play() -> None:
    """config/police/game.toml [strategy] of uoh-sqak-cop @ d07b654."""
    assert APEX_DEFAULTS["apex_w_reach"] == 1.0
    assert APEX_DEFAULTS["apex_w_dist"] == 0.6
    assert APEX_DEFAULTS["apex_w_wall"] == 0.8
    assert APEX_DEFAULTS["apex_barrier_topk"] == 3.0
    assert APEX_DEFAULTS["apex_min_gain"] == 2.0
    assert APEX_DEFAULTS["apex_barrier_cost"] == 1.0


def test_it_closes_on_the_believed_thief() -> None:
    board = make_board()
    brain = SqakApexPoliceBrain(seed=1)
    decision = brain.decide(observation(board, (0, 0)), make_belief(board, (3, 3)))
    if decision.barrier is None:
        moved = board.apply_move((0, 0), decision.move)
        assert abs(moved[0] - 3) + abs(moved[1] - 3) <= 6


def test_a_wall_it_proposes_is_always_legal() -> None:
    """Their `_candidates` is adjacency-bounded; ours must satisfy OUR barrier law."""
    board = make_board()
    brain = SqakApexPoliceBrain(seed=1)
    for thief in [(0, 2), (3, 3), (6, 6), (1, 5)]:
        state = observation(board, (0, 1))
        decision = brain.decide(state, make_belief(board, thief))
        if decision.barrier is not None:
            assert is_legal_barrier(board, (0, 1), decision.barrier,
                                    barriers_used=0, max_barriers=14)


def test_it_never_moves_and_walls_in_one_turn() -> None:
    """The Barrier Law, pinned on both sides of the league: a wall costs the step.
    The friendly's wire showed their cop doing both on 13 of 14 turns; `d07b654` fixed
    it at the chokepoint every one of their brains passes through."""
    board = make_board()
    brain = SqakApexPoliceBrain(seed=1)
    decision = brain.decide(observation(board, (1, 4)), make_belief(board, (1, 5)))
    assert decision.barrier is None or decision.move == "STAY"


def test_a_spent_quota_leaves_only_steps() -> None:
    board = make_board()
    brain = SqakApexPoliceBrain(seed=1)
    decision = brain.decide(
        observation(board, (1, 4), barriers_used=14), make_belief(board, (1, 5))
    )
    assert decision.barrier is None


def test_it_prefers_the_wall_that_strangles_the_most_area() -> None:
    """A thief one wall away from being sealed into a 2-cell pocket: the arm must
    take that wall, since area is the term their objective is dominated by."""
    walls = frozenset({(0, 2), (1, 2), (2, 2), (2, 1)})
    board = make_board(walls)
    brain = SqakApexPoliceBrain(seed=1)
    decision = brain.decide(observation(board, (1, 0), barriers_used=4),
                            make_belief(board, (0, 0)))
    assert decision.barrier == (2, 0)


def test_it_is_deterministic() -> None:
    board = make_board()
    belief = make_belief(board, (3, 3))
    first = SqakApexPoliceBrain(seed=1).decide(observation(board, (0, 0)), belief)
    second = SqakApexPoliceBrain(seed=99).decide(observation(board, (0, 0)), belief)
    assert first == second

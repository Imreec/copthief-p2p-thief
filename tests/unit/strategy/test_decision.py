"""Decision seam (TODO M5-2; PRD_police_brain §3): move XOR barrier, clamped legal.

The contract every brain rides: `decide(observation, belief) -> Decision`. A barrier
turn keeps position (reference MoveType.BARRIER semantics); an illegal barrier proposal
degrades to the legality-clamped move; quota exhaustion degrades likewise; baselines
that only implement `_pick_move` produce byte-identical moves through `decide` (the
M1-walk equivalence must survive the seam extension).
"""

import pytest

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import Board
from copthief_core.strategy.brains import BrainBase, Observation, RandomBrain
from copthief_core.strategy.decision import Decision

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


def observation(
    board: Board,
    position: tuple[int, int],
    role: str,
    *,
    barriers_used: int = 0,
    max_barriers: int = 0,
) -> Observation:
    return Observation(
        board=board,
        position=position,
        move_set=MOVE_SET,
        role=role,
        step=1,
        barriers_used=barriers_used,
        max_barriers=max_barriers,
    )


class _WallerBrain(BrainBase):
    """Always proposes a barrier at a fixed cell — exercises the barrier clamp arm."""

    def __init__(self, cell: tuple[int, int]) -> None:
        super().__init__(seed=0)
        self._cell = cell

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        return "E"

    def _decide(self, observation: Observation, belief: BeliefFilter) -> Decision:
        return Decision(barrier=self._cell)


def test_barrier_decision_keeps_position_and_reports_the_cell() -> None:
    board = make_board()
    decision = _WallerBrain((3, 4)).decide(
        observation(board, (3, 3), "police", max_barriers=2), make_belief(board, (0, 0))
    )
    assert decision.barrier == (3, 4)
    assert decision.move == "STAY"  # a barrier turn moves nothing


def test_barrier_beyond_quota_degrades_to_the_clamped_move() -> None:
    board = make_board()
    decision = _WallerBrain((3, 4)).decide(
        observation(board, (3, 3), "police", barriers_used=2, max_barriers=2),
        make_belief(board, (0, 0)),
    )
    assert decision.barrier is None
    assert decision.move == "E"


def test_non_adjacent_barrier_proposal_degrades_to_the_clamped_move() -> None:
    board = make_board()
    decision = _WallerBrain((0, 0)).decide(
        observation(board, (3, 3), "police", max_barriers=2), make_belief(board, (6, 6))
    )
    assert decision.barrier is None
    assert decision.move == "E"


def test_thief_barrier_proposal_is_refused_by_role() -> None:
    board = make_board()
    decision = _WallerBrain((3, 4)).decide(
        observation(board, (3, 3), "thief", max_barriers=2), make_belief(board, (0, 0))
    )
    assert decision.barrier is None  # the barrier law is police-only


def test_illegal_move_proposal_is_clamped_inside_decide() -> None:
    board = make_board(barriers=frozenset({(3, 4)}))  # E blocked

    class _Stubborn(BrainBase):
        def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
            return "E"

    decision = _Stubborn(seed=0).decide(
        observation(board, (3, 3), "police"), make_belief(board, (0, 0))
    )
    assert decision.barrier is None
    assert decision.move == "N"  # first sorted legal move


def test_random_brain_moves_are_byte_identical_through_decide() -> None:
    board = make_board(barriers=frozenset({(2, 3), (3, 2)}))
    belief = make_belief(board, (0, 0))
    via_pick = [
        RandomBrain(seed=7).pick_move(observation(board, (3, 3), "thief"), belief) for _ in range(1)
    ]
    via_decide = [
        RandomBrain(seed=7).decide(observation(board, (3, 3), "thief"), belief).move
        for _ in range(1)
    ]
    assert via_pick == via_decide  # the M1-walk equivalence survives the seam


def test_decision_rejects_a_barrier_combined_with_a_real_move() -> None:
    with pytest.raises(ValueError, match="barrier turn"):
        Decision(move="E", barrier=(1, 1))

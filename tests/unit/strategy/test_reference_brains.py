"""Reference-heuristic arena opponents (TODO M5-2; PRD_police_brain §2; ADR-0002).

Behavior pins for the re-derived `ref-thief` / `ref-police`: flee/chase the belief
argmax by Manhattan distance; the thief prefers unvisited cells on distance ties; the
police walls its step-cell at the attributed coin-flip rate when quota remains (a
barrier turn moves nothing), and claims ride MOVE turns only (SQ2 — enforced upstream).
Interface-mirror of observed behavior @960499fd — never reference code.
"""

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import Board
from copthief_core.strategy.brains import Observation, make_brain
from copthief_core.strategy.reference_brains import RefPoliceBrain, RefThiefBrain

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
    step: int = 1,
    barriers_used: int = 0,
    max_barriers: int = 0,
) -> Observation:
    return Observation(
        board=board,
        position=position,
        move_set=MOVE_SET,
        role=role,
        step=step,
        barriers_used=barriers_used,
        max_barriers=max_barriers,
    )


def test_ref_thief_maximizes_distance_from_the_believed_cop() -> None:
    board = make_board()
    belief = make_belief(board, (0, 0))  # cop believed at the origin corner
    decision = RefThiefBrain(seed=1).decide(observation(board, (3, 3), "thief"), belief)
    assert decision.move in {"S", "E"}  # both flee the corner
    assert decision.barrier is None


def test_ref_thief_breaks_distance_ties_toward_unvisited_cells() -> None:
    # From (3,4) with the cop believed at (3,0) and E walled, N and S tie at distance 5.
    board = make_board(barriers=frozenset({(3, 5)}))
    belief = make_belief(board, (3, 0))
    fresh = RefThiefBrain(seed=1).decide(observation(board, (3, 4), "thief"), belief).move
    assert fresh == "N"  # no history: the tie falls to the first sorted candidate
    brain = RefThiefBrain(seed=1)
    brain.decide(observation(board, (2, 4), "thief", step=1), belief)  # visits (2,4)
    second = brain.decide(observation(board, (3, 4), "thief", step=2), belief).move
    assert second == "S"  # (2,4) is now visited, so the fresh (4,4) wins the tie


def test_ref_police_minimizes_distance_when_the_coin_says_move() -> None:
    board = make_board()
    belief = make_belief(board, (0, 6))
    brain = RefPoliceBrain(seed=1, options={"ref_police_barrier_chance": 0.0})
    decision = brain.decide(observation(board, (3, 3), "police", max_barriers=14), belief)
    assert decision.barrier is None
    assert decision.move in {"N", "E"}  # both close on the argmax


def test_ref_police_walls_its_step_cell_when_the_coin_says_barrier() -> None:
    board = make_board()
    belief = make_belief(board, (0, 6))
    brain = RefPoliceBrain(seed=1, options={"ref_police_barrier_chance": 1.0})
    decision = brain.decide(observation(board, (3, 3), "police", max_barriers=14), belief)
    assert decision.move == "STAY"  # a barrier turn moves nothing
    assert decision.barrier in {(2, 3), (3, 4)}  # the cell the best move would enter


def test_ref_police_never_walls_with_quota_spent() -> None:
    board = make_board()
    belief = make_belief(board, (0, 6))
    brain = RefPoliceBrain(seed=1, options={"ref_police_barrier_chance": 1.0})
    decision = brain.decide(
        observation(board, (3, 3), "police", barriers_used=14, max_barriers=14), belief
    )
    assert decision.barrier is None


def test_reference_brains_build_by_factory_name() -> None:
    assert isinstance(make_brain("ref-thief", seed=1), RefThiefBrain)
    assert isinstance(
        make_brain("ref-police", seed=1, options={"ref_police_barrier_chance": 0.5}),
        RefPoliceBrain,
    )


def test_reference_brains_are_seed_reproducible() -> None:
    board = make_board()
    belief = make_belief(board, (0, 6))

    def run(seed: int) -> list[str]:
        brain = RefPoliceBrain(seed=seed, options={"ref_police_barrier_chance": 0.5})
        return [
            brain.decide(observation(board, (3, 3), "police", step=s, max_barriers=14), belief).move
            for s in range(1, 6)
        ]

    assert run(9) == run(9)

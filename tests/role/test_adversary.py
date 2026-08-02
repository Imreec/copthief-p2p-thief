"""Sealing-cop arena arms (TODO M7-30) — ⚑ thief repo only, never a role brain.

Opponent MODELS, not our agent: the tactic the 2026-08-01 warm-up lost s1/s3/s5 to is a
cop that walks to a camped thief and spends two of its fourteen barriers on the corner's
two gates (App E rules 46-47). Nothing in the shipped roster does that — `ref-police`
walls the cell it would have stepped into, which forgoes the step and so never closes —
so the thief's GA pool had no sealing pressure at all. These arms supply it.

Both are config-gated and inert by default: with no `seal_max_exits` they are plain
chasers, so adding them to a roster changes nothing until a config asks for sealing.
"""

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import Board
from copthief_core.strategy.brains import Observation, make_brain
from copthief_thief.adversary import BarrierCapturePoliceBrain, SealerPoliceBrain

MOVE_SET = ("N", "S", "E", "W", "STAY")
SEALER_SPEC = "copthief_thief.adversary:SealerPoliceBrain"


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
    *,
    barriers_used: int = 0,
    max_barriers: int = 14,
) -> Observation:
    return Observation(
        board=board,
        position=position,
        move_set=MOVE_SET,
        role="police",
        step=1,
        barriers_used=barriers_used,
        max_barriers=max_barriers,
        survival_threshold=35,
        max_moves=35,
    )


def test_without_options_it_is_a_plain_chaser() -> None:
    # The inert default matters: these arms join a roster, and an arm that walls by
    # default would silently rewrite every table that names it.
    board = make_board()
    belief = make_belief(board, (6, 6))
    decision = SealerPoliceBrain(seed=1).decide(observation(board, (3, 3)), belief)
    assert decision.barrier is None
    dest = board.apply_move((3, 3), decision.move)
    assert abs(dest[0] - 6) + abs(dest[1] - 6) < 6  # strictly closed the distance


def test_seals_a_gate_of_a_believed_corner_camp() -> None:
    # The warm-up geometry: thief camped at (6,6), cop on the diagonal (5,5) — from
    # there BOTH gates (5,6) and (6,5) are within the barrier law's reach.
    board = make_board()
    belief = make_belief(board, (6, 6))
    decision = SealerPoliceBrain(seed=1, options={"seal_max_exits": 2.0}).decide(
        observation(board, (5, 5)), belief
    )
    assert decision.barrier in {(5, 6), (6, 5)}


def test_never_walls_the_believed_cell_itself() -> None:
    # A barrier ON the thief's cell is a different capture form (rule 46), and an arm
    # that took it would model an oracle rather than the observed tactic. Scoped out
    # here and kept as the separate, disclosed bracket below.
    board = make_board()
    belief = make_belief(board, (5, 6))
    decision = SealerPoliceBrain(seed=1, options={"seal_max_exits": 3.0}).decide(
        observation(board, (5, 5)), belief
    )
    assert decision.barrier != (5, 6)


def test_leaves_an_open_believed_cell_alone() -> None:
    # An interior cell has four exits: sealing it would cost four barriers, so a
    # `seal_max_exits` of 2 must not fire there.
    board = make_board()
    belief = make_belief(board, (3, 4))
    decision = SealerPoliceBrain(seed=1, options={"seal_max_exits": 2.0}).decide(
        observation(board, (3, 3)), belief
    )
    assert decision.barrier is None


def test_a_spent_quota_stops_the_sealing() -> None:
    board = make_board()
    belief = make_belief(board, (6, 6))
    options = {"seal_max_exits": 2.0}
    decision = SealerPoliceBrain(seed=1, options=options).decide(
        observation(board, (5, 5), barriers_used=14, max_barriers=14), belief
    )
    assert decision.barrier is None


def test_the_bracket_arm_walls_the_believed_cell() -> None:
    # The disclosed upper bound: what a barrier-using cop with a good belief COULD do.
    # Not a model of anything observed, and never a pool member — a yardstick only.
    board = make_board()
    belief = make_belief(board, (5, 6))
    decision = BarrierCapturePoliceBrain(seed=1, options={"seal_max_exits": 2.0}).decide(
        observation(board, (5, 5)), belief
    )
    assert decision.barrier == (5, 6)


def test_deterministic_and_factory_resolvable() -> None:
    board = make_board()
    belief = make_belief(board, (6, 6))
    options = {"seal_max_exits": 2.0}
    first = SealerPoliceBrain(seed=7, options=options).decide(observation(board, (5, 5)), belief)
    again = SealerPoliceBrain(seed=7, options=options).decide(observation(board, (5, 5)), belief)
    assert first == again
    assert isinstance(make_brain(SEALER_SPEC, seed=3), SealerPoliceBrain)

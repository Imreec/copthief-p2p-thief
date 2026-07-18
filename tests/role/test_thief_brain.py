"""ThiefBrain behavior pins (TODO M5-3; PRD_thief_brain §3) — ⚑ thief repo only.

Region-survival scoring (worst-case distance + survival ramp, two-front safe region,
articulation trap-awareness against the cop's remaining quota, unvisited spread).
The brain reads the belief through its public surface, proposes through the Decision
seam, and every knob arrives via options (data-table defaults, config overrides).
"""

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import Board
from copthief_core.strategy.brains import Observation, make_brain
from copthief_thief.brain import ThiefBrain

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
    *,
    step: int = 1,
    barriers_used: int = 0,
    max_barriers: int = 14,
) -> Observation:
    return Observation(
        board=board,
        position=position,
        move_set=MOVE_SET,
        role="thief",
        step=step,
        barriers_used=barriers_used,
        max_barriers=max_barriers,
    )


def test_flees_the_certain_cop() -> None:
    board = make_board()
    belief = make_belief(board, (0, 0))
    decision = ThiefBrain(seed=1).decide(observation(board, (2, 2)), belief)
    assert decision.barrier is None
    dest = board.apply_move((2, 2), decision.move)
    assert abs(dest[0]) + abs(dest[1]) > 4  # strictly away from the corner cop


def test_prefers_the_open_side_of_a_corridor_fork() -> None:
    # A wall row splits the board: north of row 3 only a 7-cell strip remains open
    # via the (3,0) gap; south is wide open. Cop far east - distance is a wash, the
    # region term must steer south.
    walls = frozenset({(3, 1), (3, 2), (3, 3), (3, 4), (3, 5), (3, 6)})
    board = make_board(barriers=walls)
    belief = make_belief(board, (2, 6))
    decision = ThiefBrain(seed=1).decide(
        observation(board, (4, 1), barriers_used=len(walls)), belief
    )
    dest = board.apply_move((4, 1), decision.move)
    assert dest[0] >= 4  # stays in the open southern region, never through the gap


def test_articulation_penalty_rejects_a_sealable_pocket() -> None:
    # A forced corridor: from (4,5) only N (toward the cop) or S through the (5,5)
    # neck into the row-6 pocket - one barrier on the neck's feed would imprison us.
    # With quota in the cop's pocketbook the trap is refused; with quota spent, the
    # pocket is the legitimate max-distance escape and the same brain dives in.
    walls = frozenset({(5, 0), (5, 1), (5, 2), (5, 3), (5, 4), (5, 6), (4, 4), (4, 6)})
    board = make_board(barriers=walls)
    belief = make_belief(board, (3, 5))  # cop right on top of us
    with_quota = ThiefBrain(seed=1).decide(
        observation(board, (4, 5), barriers_used=len(walls), max_barriers=14), belief
    )
    dest = board.apply_move((4, 5), with_quota.move)
    assert dest != (5, 5)  # the trap entrance is refused while the cop can still seal
    spent = ThiefBrain(seed=1).decide(
        observation(board, (4, 5), barriers_used=14, max_barriers=14), belief
    )
    dest_spent = board.apply_move((4, 5), spent.move)
    assert dest_spent == (5, 5)  # quota spent: the pocket is safe ground again


def test_survival_ramp_dominates_near_the_threshold() -> None:
    board = make_board()
    belief = make_belief(board, (3, 1))  # cop closing from the west
    early = ThiefBrain(seed=1).decide(observation(board, (3, 3), step=2), belief)
    late = ThiefBrain(seed=1).decide(observation(board, (3, 3), step=33), belief)
    early_dest = board.apply_move((3, 3), early.move)
    late_dest = board.apply_move((3, 3), late.move)
    late_gap = abs(late_dest[0] - 3) + abs(late_dest[1] - 1)
    assert late_gap >= abs(early_dest[0] - 3) + abs(early_dest[1] - 1)
    assert late_gap == 3  # at the clock's edge nothing beats pure flight


def test_decisions_are_deterministic_and_factory_resolvable() -> None:
    board = make_board(barriers=frozenset({(2, 3)}))
    belief = make_belief(board, (0, 6))
    first = ThiefBrain(seed=7).decide(observation(board, (3, 3)), belief)
    again = ThiefBrain(seed=7).decide(observation(board, (3, 3)), belief)
    assert first == again
    assert isinstance(make_brain("copthief_thief.brain:ThiefBrain", seed=3), ThiefBrain)

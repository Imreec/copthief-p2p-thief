"""DoctrineEvaderBrain (M9-3/M9-4) — the thief that refuses the counted-loss death.

Score order (lexicographic): survive the next turn (lethal gate), then the
anti-camp stay cap, then capped flight, then the worst-wall forecast terms.
The gate sits ABOVE flight because inside a forming seal "away from the cop"
is measured the long way round; the flee cap sits above the forecast because
their measured doctrine ranks it so — and lifts only when the belief says the
hunter is actually near (the fresh_flee lesson: react to threat NEAR US).
"""

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import STAY, Board, Coord
from copthief_core.strategy.brains import Observation
from copthief_core.strategy.doctrine_evader import DoctrineEvaderBrain

MOVE_SET = ("N", "S", "E", "W", "STAY")


def make_board(barriers: frozenset[Coord] = frozenset()) -> Board:
    return Board(grid_size=7, axis_origin_corner="top-left", axis_start_index=0, barriers=barriers)


def make_belief(board: Board, cop_cell: Coord) -> BeliefFilter:
    return BeliefFilter(
        board=board,
        move_set=MOVE_SET,
        start=cop_cell,
        center_intensity=0.9,
        decay=0.1,
        smell_trust=0.0,
        hint_trust=0.0,
    )


def make_observation(board: Board, position: Coord) -> Observation:
    return Observation(
        board=board,
        position=position,
        move_set=MOVE_SET,
        role="thief",
        step=10,
        barriers_used=0,
        max_barriers=14,
        max_moves=35,
    )


def test_the_only_survivable_move_is_taken() -> None:
    """Thief at (5,6) with (6,5) walled, cop certain at (5,5): STAY and W die to
    a step-on, S dies to the (5,6) imprisoning wall — N is the one way out."""
    board = make_board(frozenset({(6, 5)}))
    brain = DoctrineEvaderBrain(seed=3)
    move = brain.pick_move(make_observation(board, (5, 6)), make_belief(board, (5, 5)))
    assert move == "N"


def test_open_board_prefers_open_ground_over_the_edge() -> None:
    """Cop far away: capped flight saturates, so the forecast terms rule — the
    thief keeps its escape count at 4 instead of drifting to the edge (the
    counted-loss corner walk, refused at its first step)."""
    board = make_board()
    brain = DoctrineEvaderBrain(seed=3)
    move = brain.pick_move(make_observation(board, (5, 5)), make_belief(board, (0, 0)))
    dest = board.apply_move((5, 5), move)
    assert sum(1 for n in board.neighbors(dest) if not board.is_blocked(n)) == 4


def test_stay_cap_breaks_the_camp() -> None:
    """Uncapped flight makes the corner a STAY-magnet (the g02 geometry); after
    `stay_cap_limit` consecutive STAYs the cap forces motion anyway."""
    board = make_board()
    brain = DoctrineEvaderBrain(seed=3, options={"safe_distance": 99.0, "stay_cap_limit": 2.0})
    observation = make_observation(board, (6, 6))
    belief = make_belief(board, (0, 0))
    moves = [brain.pick_move(observation, belief) for _ in range(3)]
    assert moves[0] == STAY
    assert moves[1] == STAY
    assert moves[2] != STAY


def test_hunted_thief_flees_instead_of_idling() -> None:
    """Cop mass near us lifts the flee cap: with the cop certain at (3,1) the
    doctrine takes E — maximum real separation — not a tie-break shuffle."""
    board = make_board()
    brain = DoctrineEvaderBrain(seed=3)
    move = brain.pick_move(make_observation(board, (3, 3)), make_belief(board, (3, 1)))
    assert move == "E"

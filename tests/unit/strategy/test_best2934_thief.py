"""best2934 thief arm (M7-45, rebuilt at their 5324415 for M12).

Modelled from their PUBLISHED brain (github.com/Krayz1a/best2934-thief, MIT, (c) 2026
Tomer Levy / Eyal Koloshi / Alon Issman) after the 2026-08-14 evening friendly: the
corner-runner script is gone; the shipped policy adds an exit-counting veto chain in
front of the M7-45 score. Each test pins one behaviour our own logs showed live
(g02/g04/g06) or their code makes exact, because an arm that plays like
`greedy-manhattan` measures nothing about them.
"""

from pathlib import Path

from copthief_core.shared.config import load_all
from copthief_core.strategy.best2934_thief import Best2934ThiefBrain
from copthief_core.strategy.brains import Observation
from copthief_core.strategy.referee_setup import referee_belief

CONSTITUTION, PRIVATE, _ = load_all(Path("config"), counted=False)
TRUST = PRIVATE.smell_trust_weight


def _observation(board: object, position: tuple[int, int], **kw: object) -> Observation:
    return Observation(
        board=board,  # type: ignore[arg-type]
        position=position,
        move_set=CONSTITUTION.movement.move_set,
        role="thief",
        step=int(kw.pop("step", 1)),
        survival_threshold=int(kw.pop("survival_threshold", 35)),
        barriers_used=int(kw.pop("barriers_used", 0)),
        max_barriers=int(kw.pop("max_barriers", 0)),
    )


def _delta_belief(cell: tuple[int, int]) -> object:
    return referee_belief(CONSTITUTION, start=cell, smell_trust=TRUST)


def test_the_thief_refuses_to_enter_a_two_exit_corner_while_alternatives_exist() -> None:
    """THE veto their #45 disclosure named: a corner has two exits, so it never goes in.

    From (0,1) with the believed cop at (2,3), raw distance ranks the corner (0,0)
    first — the old script-era arm walks straight in. The shipped thief refuses any
    <=2-exit destination while an alternative exists (108/108 decisions in our g02/
    g04/g06 logs never entered a corner). Whatever the score picks, it is not W.
    """
    board = CONSTITUTION.board.make_board()
    brain = Best2934ThiefBrain(seed=1)
    move = brain.pick_move(_observation(board, (0, 1)), _delta_belief((2, 3)))
    assert board.apply_move((0, 1), move) != (0, 0)


def test_the_thief_leaves_a_one_exit_cell_rather_than_standing_in_it() -> None:
    """Their disclosed rule, verbatim; STAY is dropped whenever the seat has one exit."""
    board = CONSTITUTION.board.make_board().with_barrier((1, 0))
    brain = Best2934ThiefBrain(seed=1)
    move = brain.pick_move(_observation(board, (0, 0)), _delta_belief((0, 3)))
    assert move == "E"  # the only remaining exit, even though it closes on the cop


def test_ties_resolve_in_their_move_order_north_first() -> None:
    """Their argmax is strict with candidates in board order N > S > E > W > STAY.

    From (3,3) with the believed cop at (3,0), N/S/E all achieve distance 4 and the
    area term cancels; their first-wins argmax takes N. The old arm's alphabetical
    tie-break took S — this pin is what makes the rebuild measurable.
    """
    board = CONSTITUTION.board.make_board()
    brain = Best2934ThiefBrain(seed=1)
    move = brain.pick_move(_observation(board, (3, 3)), _delta_belief((3, 0)))
    assert move == "N"


def test_the_g04_shape_stands_once_in_a_two_exit_cell_but_flees_an_adjacent_peak() -> None:
    """The live reroute our (6,4) wall forced (g04/g06 step 11-12), reproduced.

    The entering-veto does not evict a thief already IN a 2-exit cell ("refuses a
    cell" is about entry; only a ONE-exit seat forces departure — their own two
    disclosed sentences). At (6,5) with (6,4) walled: E is the vetoed corner, and
    while the believed cop sits at (4,5) the N step is peak-adjacent (-6), so it
    stands one turn. The moment the peak reaches (6,6), STAY itself is peak-adjacent
    and it breaks north — exactly the logged sequence.
    """
    board = CONSTITUTION.board.make_board().with_barrier((6, 4))
    brain = Best2934ThiefBrain(seed=1)
    stands = brain.pick_move(_observation(board, (6, 5)), _delta_belief((4, 5)))
    assert stands == "STAY"
    breaks = brain.pick_move(_observation(board, (6, 5)), _delta_belief((6, 6)))
    assert breaks == "N"


def test_the_thief_is_penalised_for_standing_still() -> None:
    """IDLE_PENALTY (1.0): camping saturates their own scent field and paints a target."""
    board = CONSTITUTION.board.make_board()
    brain = Best2934ThiefBrain(seed=1)
    move = brain.pick_move(_observation(board, (3, 3)), _delta_belief((3, 1)))
    assert move != "STAY"


def test_the_area_term_still_cancels_on_the_negotiated_board() -> None:
    """Held over from the M7-45 finding: their `reachable_area(cell, limit=60)` counts
    cells, the negotiated board has 49, and every candidate stays connected through
    the thief's own cell — the term cancels out of the comparison. The veto chain
    reads exit COUNTS, not areas, so ablating the weight still moves nothing.
    """
    board = CONSTITUTION.board.make_board()
    for cell in ((0, 2), (1, 2), (2, 2), (2, 1)):
        board = board.with_barrier(cell)
    observation = _observation(board, (1, 1))
    belief = _delta_belief((5, 1))
    none = Best2934ThiefBrain(seed=1, options={"area_weight": 0.0}).pick_move(observation, belief)
    lots = Best2934ThiefBrain(seed=1, options={"area_weight": 100.0}).pick_move(observation, belief)
    assert none == lots

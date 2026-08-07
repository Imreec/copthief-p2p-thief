"""best2934 opponent arms (M7-45) — the arena stand-ins for our second counted opponent.

Modelled from their PUBLISHED brains (github.com/Krayz1a/best2934-cop, MIT, (c) 2026
Tomer Levy / Eyal Koloshi / Alon Issman), same practice as M7-14's `belief-evader` for
anrbj666. Each test pins the ONE behaviour that distinguishes their policy from the
baselines we already field, because an arm that plays like `greedy-manhattan` measures
nothing about them.
"""

from pathlib import Path

from copthief_core.shared.config import load_all
from copthief_core.strategy.best2934_cop import Best2934CopBrain
from copthief_core.strategy.brains import Observation
from copthief_core.strategy.referee_setup import referee_belief

CONSTITUTION, PRIVATE, _ = load_all(Path("config"), counted=False)
TRUST = PRIVATE.smell_trust_weight


def _observation(board: object, position: tuple[int, int], role: str, **kw: object) -> Observation:
    return Observation(
        board=board,  # type: ignore[arg-type]
        position=position,
        move_set=CONSTITUTION.movement.move_set,
        role=role,
        step=int(kw.pop("step", 1)),
        survival_threshold=int(kw.pop("survival_threshold", 0)),
        barriers_used=int(kw.pop("barriers_used", 0)),
        max_barriers=int(kw.pop("max_barriers", 0)),
    )


def _delta_belief(cell: tuple[int, int]) -> object:
    return referee_belief(CONSTITUTION, start=cell, smell_trust=TRUST)


def test_the_cop_closes_on_the_belief_peak() -> None:
    """Their movement term is greedy descent on belief-weighted distance."""
    board = CONSTITUTION.board.make_board()
    brain = Best2934CopBrain(seed=1)
    move = brain.pick_move(_observation(board, (3, 3), "police"), _delta_belief((3, 6)))
    assert move == "E"  # (3,3) -> (3,6) is three columns east under the top-left origin


def test_the_cop_does_not_wall_beyond_its_engage_range() -> None:
    """THE fielded parameter, and the one that makes them dangerous or harmless:
    `barrier_engage_range` was tuned 4 -> 1 on their own sweep (capture 1.000 at range
    1, 0.000 at range 3). Beyond it a wall costs a turn of movement for nothing, so
    they move instead. At distance 3 the decision must be a move, never a barrier."""
    board = CONSTITUTION.board.make_board()
    brain = Best2934CopBrain(seed=1, options={"barrier_engage_range": 1})
    decision = brain.decide(
        _observation(board, (3, 3), "police", max_barriers=14), _delta_belief((3, 6))
    )
    assert decision.barrier is None


def test_the_cop_seals_at_contact_range() -> None:
    """Inside the engage range a barrier that shrinks the thief's reachable area by at
    least `barrier_min_gain` is worth the turn. This is the rule-46 enclosure capture
    that won both of their live sub-games against gal-roy1."""
    board = CONSTITUTION.board.make_board()
    for cell in ((0, 1), (1, 1)):  # thief in the top-left pocket, one mouth left at (2,0)
        board = board.with_barrier(cell)
    brain = Best2934CopBrain(seed=1, options={"barrier_engage_range": 1})
    decision = brain.decide(
        _observation(board, (1, 0), "police", max_barriers=14), _delta_belief((0, 0))
    )
    assert decision.barrier is not None
    assert decision.move == "STAY"


def test_the_cop_holds_its_endgame_reserve() -> None:
    """BARRIER_ENDGAME_RESERVE (3): with the quota nearly spent they only wall for a
    squeeze they can finish (distance <= 2), so a marginal seal is declined."""
    board = CONSTITUTION.board.make_board()
    for cell in ((0, 1), (1, 1)):
        board = board.with_barrier(cell)
    brain = Best2934CopBrain(seed=1, options={"barrier_engage_range": 1})
    decision = brain.decide(
        _observation(board, (1, 0), "police", barriers_used=12, max_barriers=14),
        _delta_belief((0, 0)),
    )
    assert decision.barrier is not None  # distance 1 <= 2, still inside the squeeze

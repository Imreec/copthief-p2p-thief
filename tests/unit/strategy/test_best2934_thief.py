"""best2934 opponent arms (M7-45) — the arena stand-ins for our second counted opponent.

Modelled from their PUBLISHED brains (github.com/Krayz1a/best2934-cop, MIT, (c) 2026
Tomer Levy / Eyal Koloshi / Alon Issman), same practice as M7-14's `belief-evader` for
anrbj666. Each test pins the ONE behaviour that distinguishes their policy from the
baselines we already field, because an arm that plays like `greedy-manhattan` measures
nothing about them.
"""

from pathlib import Path

from copthief_core.shared.config import load_all
from copthief_core.strategy.best2934_thief import Best2934ThiefBrain
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


def test_the_thief_adjacency_penalty_is_inert_too() -> None:
    """⚠ SECOND finding, same shape as the first.

    ADJACENCY_PENALTY (6.0) subtracts from any destination within one step of the
    belief peak. But "within one step of the peak" IS "distance to the peak <= 1", and
    a distance-maximiser already ranks those last. So the penalty re-punishes exactly
    the cells the main term has already rejected, and can only bite when EVERY legal
    destination is adjacent to the peak — geometry that also means the thief is
    already caught. Ablating 6.0 -> 0.0 changes nothing anywhere on an open board.
    """
    board = CONSTITUTION.board.make_board()
    belief = _delta_belief((3, 6))
    for position in ((3, 5), (2, 6), (3, 3), (0, 0), (6, 6)):
        observation = _observation(board, position, "thief")
        penalised = Best2934ThiefBrain(seed=1).pick_move(observation, belief)
        ablated = Best2934ThiefBrain(seed=1, options={"adjacency_penalty": 0.0}).pick_move(
            observation, belief
        )
        assert penalised == ablated, position


def test_the_thief_area_term_is_inert_on_the_negotiated_board() -> None:
    """⚠ A REAL FINDING, pinned deliberately rather than papered over.

    Their module docstring calls reachable area "the dominant term". It cannot be, on
    the board we actually play. Their `reachable_area(cell, limit=60)` counts CELLS
    (not BFS depth) and the negotiated board has 49, so the cap never bites; and every
    destination the thief can reach stays connected to every other through the thief's
    OWN cell, which the flood fill never removes. So the term returns one identical
    number for every candidate and cancels out of the comparison.

    Their shipped thief therefore reduces to a distance-maximiser with an adjacency
    penalty. Ablating the weight from 0 to 100 must not move a single choice.
    """
    board = CONSTITUTION.board.make_board()
    for cell in ((0, 2), (1, 2), (2, 2), (2, 1)):  # walls do not rescue it either
        board = board.with_barrier(cell)
    observation = _observation(board, (1, 1), "thief")
    belief = _delta_belief((5, 1))
    none = Best2934ThiefBrain(seed=1, options={"area_weight": 0.0}).pick_move(observation, belief)
    lots = Best2934ThiefBrain(seed=1, options={"area_weight": 100.0}).pick_move(observation, belief)
    assert none == lots


def test_the_thief_endgame_switch_cannot_change_the_choice() -> None:
    """⚠ THIRD finding, and it follows from the first two.

    The endgame rescales distance 1.2 -> 2.0 and area 0.25 -> 0.05. Area is inert, so
    the switch multiplies the ONLY live term by a positive constant — which cannot
    move an argmax. All it does is shrink the idle penalty's relative weight, making a
    thief that already refuses to camp refuse slightly harder.
    """
    board = CONSTITUTION.board.make_board()
    belief = _delta_belief((0, 3))
    for position in ((1, 3), (3, 3), (5, 5), (6, 0)):
        early = Best2934ThiefBrain(seed=1).pick_move(
            _observation(board, position, "thief", step=1, survival_threshold=35), belief
        )
        late = Best2934ThiefBrain(seed=1).pick_move(
            _observation(board, position, "thief", step=33, survival_threshold=35), belief
        )
        assert early == late, position


def test_their_thief_reduces_to_a_greedy_distance_maximiser() -> None:
    """THE PUNCHLINE, and the reason this arm was worth building.

    With area, adjacency and the endgame switch all structurally inert, their shipped
    thief is a greedy distance-maximiser that will not camp. Checked by outcome rather
    than by move name, because their tie-break is alphabetical and the baseline's is
    reverse-alphabetical: the DISTANCE ACHIEVED must match `greedy-manhattan` on every
    cell of the board.
    """
    from copthief_core.strategy.brains import make_brain

    board = CONSTITUTION.board.make_board()
    theirs = Best2934ThiefBrain(seed=1)
    baseline = make_brain("greedy-manhattan", seed=1)
    peak = (3, 3)
    belief = _delta_belief(peak)
    for row in range(7):
        for col in range(7):
            if (row, col) == peak:
                continue
            observation = _observation(board, (row, col), "thief")
            ours = board.apply_move((row, col), theirs.pick_move(observation, belief))
            base = board.apply_move((row, col), baseline.pick_move(observation, belief))
            assert abs(ours[0] - peak[0]) + abs(ours[1] - peak[1]) == abs(base[0] - peak[0]) + abs(
                base[1] - peak[1]
            ), (row, col)


def test_the_thief_is_penalised_for_standing_still() -> None:
    """IDLE_PENALTY (1.0): camping saturates their own scent field and paints a target."""
    board = CONSTITUTION.board.make_board()
    brain = Best2934ThiefBrain(seed=1)
    move = brain.pick_move(_observation(board, (3, 3), "thief"), _delta_belief((3, 1)))
    assert move != "STAY"

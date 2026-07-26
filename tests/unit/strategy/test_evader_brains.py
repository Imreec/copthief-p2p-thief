"""BeliefEvaderBrain — the trap-aware evader opponent model (M7-14).

The arena stand-in for the opponent's announced counter (belief-native trap
awareness), with priorities ordered by the M7-13 capture postmortem: flee the
BELIEVED cop first (both captures were opponent-position-modeling failures), refuse
to camp under threat (g02: ten terminal STAYs made a scent beacon; in corner
geometry STAY even MAXIMIZES Manhattan distance — the trap the penalty breaks), and
forecast walls via destination mobility + reachable region (his announced fix).
"""

from pathlib import Path

from copthief_core.shared.config import load_all
from copthief_core.strategy.evader_brains import BeliefEvaderBrain
from copthief_core.strategy.referee_setup import referee_belief

CONSTITUTION, PRIVATE, _ = load_all(Path("config"), counted=False)
TRUST = PRIVATE.smell_trust_weight


def _observation(board: object, position: tuple[int, int]) -> object:
    from copthief_core.strategy.brains import Observation

    return Observation(
        board=board,  # type: ignore[arg-type]
        position=position,
        move_set=CONSTITUTION.movement.move_set,
        role="thief",
        step=1,
    )


def _delta_belief(cell: tuple[int, int]) -> object:
    return referee_belief(CONSTITUTION, start=cell, smell_trust=TRUST)


def test_the_evader_flees_the_believed_cop() -> None:
    board = CONSTITUTION.board.make_board()
    brain = BeliefEvaderBrain(seed=1)
    move = brain.pick_move(_observation(board, (3, 4)), _delta_belief((3, 3)))  # type: ignore[arg-type]
    assert move == "E"


def test_the_evader_routes_around_a_dead_end_pocket() -> None:
    """Equal flight distance both ways; one destination is a one-exit pocket. A
    trap-naive evader flips a coin — the wall forecast must refuse the pocket."""
    board = CONSTITUTION.board.make_board()
    for cell in ((2, 2), (4, 2), (3, 1)):
        board = board.with_barrier(cell)
    brain = BeliefEvaderBrain(seed=1)
    move = brain.pick_move(_observation(board, (3, 3)), _delta_belief((0, 3)))  # type: ignore[arg-type]
    assert move != "W"


def test_the_evader_refuses_to_camp_under_threat() -> None:
    """g02's geometry: from a corner, STAY maximizes Manhattan distance to a
    diagonal cop — exactly the beacon camp that lost the friendly. The anti-camp
    penalty must force motion when the believed cop is inside the threat radius."""
    board = CONSTITUTION.board.make_board()
    brain = BeliefEvaderBrain(seed=1)
    move = brain.pick_move(_observation(board, (0, 0)), _delta_belief((2, 2)))  # type: ignore[arg-type]
    assert move != "STAY"


def test_without_the_penalty_the_corner_camp_is_the_distance_optimum() -> None:
    """The control arm: zeroing the anti-camp knob reproduces the opponent's current
    behavior (camping is DISTANCE-OPTIMAL in corner geometry — that is the finding)."""
    board = CONSTITUTION.board.make_board()
    brain = BeliefEvaderBrain(
        seed=1, options={"stay_penalty": 0.0, "w_mobility": 0.0, "w_region": 0.0}
    )
    move = brain.pick_move(_observation(board, (0, 0)), _delta_belief((2, 2)))  # type: ignore[arg-type]
    assert move == "STAY"


def test_the_evader_is_deterministic() -> None:
    board = CONSTITUTION.board.make_board()
    moves = [
        BeliefEvaderBrain(seed=7).pick_move(_observation(board, (3, 4)), _delta_belief((5, 1)))  # type: ignore[arg-type]
        for _ in range(3)
    ]
    assert len(set(moves)) == 1

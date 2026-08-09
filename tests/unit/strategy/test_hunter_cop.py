"""Hunter-cop stress arm pins (M9 study) — anrbj666's `AgedBeliefTrapCop` policy.

Pins the hunting pattern OUR thief must survive: BFS-greedy closing on the belief
peak, the low-mass pounce gate, the surgical pocket wall inside trap range, and the
rule-46 kill wall on a sharp adjacent peak.
"""

from pathlib import Path

from copthief_core.shared.config import load_all
from copthief_core.strategy.brains import Observation, make_brain
from copthief_core.strategy.hunter_cop import HUNTER_DEFAULTS, HunterCopBrain
from copthief_core.strategy.referee_setup import referee_belief

CONSTITUTION, PRIVATE, _ = load_all(Path("config"), counted=False)
TRUST = PRIVATE.smell_trust_weight


def _observation(board: object, position: tuple[int, int], **kw: object) -> Observation:
    return Observation(
        board=board,  # type: ignore[arg-type]
        position=position,
        move_set=CONSTITUTION.movement.move_set,
        role="police",
        step=int(kw.pop("step", 1)),
        barriers_used=int(kw.pop("barriers_used", 0)),
        max_barriers=int(kw.pop("max_barriers", CONSTITUTION.movement.max_barriers)),
    )


def _delta_belief(cell: tuple[int, int]) -> object:
    return referee_belief(CONSTITUTION, start=cell, smell_trust=TRUST)


def test_a_collapsed_belief_two_off_pulls_it_straight_in() -> None:
    """Closing is BFS descent on the peak; the open-board step east is unique."""
    board = CONSTITUTION.board.make_board()
    brain = make_brain("hunter-cop", seed=1)
    decision = brain.decide(_observation(board, (3, 3)), _delta_belief((3, 5)))
    assert decision.barrier is None  # open board: no wall clears gain_min
    assert decision.move == "E"


def test_it_routes_around_walls_where_the_vibecode_cop_dithers() -> None:
    """BFS-greedy, not Manhattan-blind: with the direct cell walled and the north
    detour also sealed, only the southern route shortens the true path."""
    board = CONSTITUTION.board.make_board().with_barrier((3, 4)).with_barrier((2, 4))
    brain = HunterCopBrain(seed=1)
    decision = brain.decide(_observation(board, (3, 3), barriers_used=2), _delta_belief((3, 5)))
    assert decision.move == "S"


def test_a_sharp_adjacent_peak_gets_the_rule_46_kill_wall() -> None:
    """Their KILL_MASS branch: a collapsed belief in placement reach is walled
    directly — a barrier on the thief's cell captures outright."""
    board = CONSTITUTION.board.make_board()
    decision = HunterCopBrain(seed=1).decide(_observation(board, (3, 3)), _delta_belief((3, 4)))
    assert decision.barrier == (3, 4)
    assert decision.move == "STAY"


def test_a_two_exit_pocket_in_reach_gets_the_escape_walled() -> None:
    """The surgical wall: the believed thief sits in a pocket whose mouth is in our
    placement reach, and sealing it strips the whole open board from its room."""
    board = CONSTITUTION.board.make_board().with_barrier((1, 0))
    decision = HunterCopBrain(seed=1).decide(
        _observation(board, (0, 2), barriers_used=1), _delta_belief((0, 0))
    )
    assert decision.barrier == (0, 1)
    assert decision.move == "STAY"


def test_below_the_pounce_mass_it_keeps_moving() -> None:
    """The gate that makes it a POUNCER, not a sniper: mass under the threshold
    means no wall is considered at all, even with the kill geometry on the board."""
    board = CONSTITUTION.board.make_board()
    over_gate = float(HUNTER_DEFAULTS["pounce_mass"]) + 1.0
    decision = HunterCopBrain(seed=1, options={"pounce_mass": over_gate}).decide(
        _observation(board, (3, 3)), _delta_belief((3, 4))
    )
    assert decision.barrier is None
    assert decision.move == "E"  # it closes onto the peak cell instead of walling

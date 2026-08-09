"""vibecode cop arm pins (M9 study) — the audit-revealed east-waller.

Pins the signature behaviors read off anrbj666's archived logs
(P2P-Thief/results/log_anrbj666-vs-vibecode_g02/g04/g06.json): the S,S opening, the
step-3 PLACE_E at (2,1), the east-biased wall habit, the wasted re-placement on an
already-walled cell, and the wall-blind chase that produced its dithering. Brains
carry no claim surface, so the claim-less record is pinned structurally: a Decision
is only ever a move or a barrier.
"""

from pathlib import Path

from copthief_core.shared.config import load_all
from copthief_core.strategy.brains import Observation, make_brain
from copthief_core.strategy.referee_setup import referee_belief
from copthief_core.strategy.vibecode_cop import VibecodeCopBrain

CONSTITUTION, PRIVATE, _ = load_all(Path("config"), counted=False)
TRUST = PRIVATE.smell_trust_weight
SPAWN = (0, 0)  # the logged cop spawn, wire [0,0]


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


def test_it_opens_with_two_south_marches() -> None:
    """Steps 1-2 in g02/g04/g06: S then S out of the spawn, no barrier."""
    board = CONSTITUTION.board.make_board()
    brain = make_brain("vibecode-police", seed=1)
    belief = _delta_belief((6, 6))
    position = SPAWN
    for step in (1, 2):
        decision = brain.decide(_observation(board, position, step=step), belief)
        assert (decision.move, decision.barrier) == ("S", None)
        position = board.apply_move(position, decision.move)
    assert position == (2, 0)


def test_the_early_wall_is_the_logged_place_e_at_step_three() -> None:
    """g02/g04 step 3: PLACE_E from wire [0,2], the barrier at wire [1,2] = (2,1)."""
    board = CONSTITUTION.board.make_board()
    decision = VibecodeCopBrain(seed=1).decide(
        _observation(board, (2, 0), step=3), _delta_belief((6, 6))
    )
    assert decision.barrier == (2, 1)
    assert decision.move == "STAY"


def test_the_wall_habit_places_east_of_itself_mid_board() -> None:
    """16 of 18 logged placements were PLACE_E; on a habit step the wall is east."""
    board = CONSTITUTION.board.make_board()
    decision = VibecodeCopBrain(seed=1).decide(
        _observation(board, (3, 4), step=7), _delta_belief((6, 6))
    )
    assert decision.barrier == (3, 5)


def test_a_habit_step_on_a_walled_cell_burns_the_turn() -> None:
    """g02 steps 31-32: re-attempting an already-walled cell forfeits the move."""
    board = CONSTITUTION.board.make_board().with_barrier((3, 5))
    decision = VibecodeCopBrain(seed=1).decide(
        _observation(board, (3, 4), step=7), _delta_belief((6, 6))
    )
    assert decision.barrier is None
    assert decision.move == "STAY"


def test_off_habit_steps_chase_the_belief_peak_wall_blind() -> None:
    """The dithering seed: Manhattan descent toward the argmax, never idle."""
    board = CONSTITUTION.board.make_board()
    brain = VibecodeCopBrain(seed=1)
    decision = brain.decide(_observation(board, (3, 4), step=8), _delta_belief((6, 6)))
    assert decision.barrier is None
    assert decision.move in {"S", "E"}  # both close on (6,6); the tie is deterministic
    # Wall-blindness: with the direct cell walled it still steps by straight-line
    # distance (the observed 2-cell dither), not around via a BFS detour.
    walled = board.with_barrier((3, 5))
    dither = brain.decide(_observation(walled, (3, 4), step=8), _delta_belief((3, 6)))
    assert dither.move in {"N", "S"}


def test_a_decision_is_only_ever_a_move_or_a_wall() -> None:
    """No claim surface, no hint intent: the arm never reaches for the verbal layer."""
    board = CONSTITUTION.board.make_board()
    brain = VibecodeCopBrain(seed=1)
    belief = _delta_belief((6, 6))
    for step in range(1, 12):
        decision = brain.decide(_observation(board, (2, 2), step=step), belief)
        assert decision.hint_verdict is None
        assert decision.hint_landmark is None

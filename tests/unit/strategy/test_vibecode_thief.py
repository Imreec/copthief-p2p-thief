"""vibecode thief arm pins (M9 study) — the audit-revealed corner oscillator.

Pins the signature behaviors read off anrbj666's archived logs
(P2P-Police/results/log_anrbj666-vs-vibecode_g01/g03/g05.json): south edge by step
3, an input-dependent corner run, the endless corner<->neighbor oscillation, and the
two absences that make it cheap to beat — never STAY, never a barrier.
"""

from pathlib import Path

from copthief_core.shared.config import load_all
from copthief_core.strategy.brains import Observation, make_brain
from copthief_core.strategy.referee_setup import referee_belief
from copthief_core.strategy.vibecode_thief import VibecodeThiefBrain

CONSTITUTION, PRIVATE, _ = load_all(Path("config"), counted=False)
TRUST = PRIVATE.smell_trust_weight
START = (3, 3)  # the logged spawn, wire [3,3]


def _observation(board: object, position: tuple[int, int], *, step: int = 1) -> Observation:
    return Observation(
        board=board,  # type: ignore[arg-type]
        position=position,
        move_set=CONSTITUTION.movement.move_set,
        role="thief",
        step=step,
    )


def _delta_belief(cell: tuple[int, int]) -> object:
    return referee_belief(CONSTITUTION, start=cell, smell_trust=TRUST)


def _run(brain: VibecodeThiefBrain, cop_at: tuple[int, int], steps: int) -> list[tuple[int, int]]:
    """Play the arm open-loop from the logged spawn; Output: the visited positions."""
    board = CONSTITUTION.board.make_board()
    belief = _delta_belief(cop_at)
    position, trail = START, []
    for step in range(1, steps + 1):
        move = brain.pick_move(_observation(board, position, step=step), belief)
        assert move != "STAY", (step, position)
        position = board.apply_move(position, move)
        trail.append(position)
    return trail


def test_it_reaches_the_south_edge_by_step_three() -> None:
    """g01/g03/g05 step 3: wire [3,6] — three S moves out of the spawn."""
    trail = _run(make_brain("vibecode-thief", seed=1), (0, 0), 3)  # type: ignore[arg-type]
    assert trail == [(4, 3), (5, 3), (6, 3)]


def test_a_west_believed_cop_sends_it_to_the_east_corner() -> None:
    """g01/g03: the cop opened on the west column, the thief ran east to [6,6]."""
    trail = _run(VibecodeThiefBrain(seed=1), (0, 0), 6)
    assert trail[-1] == (6, 6)


def test_an_east_believed_cop_sends_it_to_the_west_corner() -> None:
    """g05's shape: the corner pick flees the believed cop's half of the board."""
    trail = _run(VibecodeThiefBrain(seed=1), (0, 6), 6)
    assert trail[-1] == (6, 0)


def test_it_ends_the_clock_oscillating_between_corner_and_neighbor() -> None:
    """g05 steps 7-35: a strict two-cell loop on the edge, never anything else."""
    trail = _run(VibecodeThiefBrain(seed=1), (0, 0), CONSTITUTION.movement.survival_threshold)
    tail = trail[len(trail) // 2 :]
    assert set(tail) == {(6, 6), (6, 5)}
    assert all(a != b for a, b in zip(tail, tail[1:], strict=False))


def test_it_never_proposes_a_barrier() -> None:
    """All 61 logged thief steps carry barrier_placed null; the arm has no wall path."""
    board = CONSTITUTION.board.make_board()
    brain = VibecodeThiefBrain(seed=1)
    belief = _delta_belief((0, 0))
    for position in ((3, 3), (6, 3), (6, 6), (6, 5)):
        decision = brain.decide(_observation(board, position), belief)
        assert decision.barrier is None
        assert decision.move != "STAY"

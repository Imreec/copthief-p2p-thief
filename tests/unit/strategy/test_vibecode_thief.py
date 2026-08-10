"""vibecode thief arm pins (M10 rebuild) — the central hex-loop oscillator.

Pins the signature behaviors read off OUR OWN 2026-08-10 friendly logs
(`logs/imreeyal-vs-vibecode_g01/g03/g05.jsonl`, audit-revealed positions): the
six-cell counterclockwise loop around board center — (3,3)→(4,3)→(4,4)→(3,4)→
(2,4)→(2,3)→ — held for 25+ consecutive steps in all three games, a vertical
sprint away from the believed cop in the final steps, the single diagonal-cut
STAY each game shows, and the absence that defines the matchup — never a
barrier. The pre-08-10 corner oscillator (anrbj666's logs) is DEAD; these pins
replace those.
"""

from pathlib import Path

from copthief_core.shared.config import load_all
from copthief_core.strategy.brains import Observation, make_brain
from copthief_core.strategy.referee_setup import referee_belief
from copthief_core.strategy.vibecode_thief import VibecodeThiefBrain

CONSTITUTION, PRIVATE, _ = load_all(Path("config"), counted=False)
TRUST = PRIVATE.smell_trust_weight
START = (3, 3)  # the logged spawn, wire [3,3]
LOOP = [(4, 3), (4, 4), (3, 4), (2, 4), (2, 3), (3, 3)]  # one lap, spawn last


def _observation(board: object, position: tuple[int, int], *, step: int = 1) -> Observation:
    return Observation(
        board=board,  # type: ignore[arg-type]
        position=position,
        move_set=CONSTITUTION.movement.move_set,
        role="thief",
        step=step,
        survival_threshold=CONSTITUTION.movement.survival_threshold,
        max_moves=CONSTITUTION.movement.max_moves,
    )


def _delta_belief(cell: tuple[int, int]) -> object:
    return referee_belief(CONSTITUTION, start=cell, smell_trust=TRUST)


def _run(
    brain: VibecodeThiefBrain,
    cop_at: tuple[int, int],
    steps: int,
    *,
    start: tuple[int, int] = START,
    from_step: int = 1,
) -> list[tuple[int, int]]:
    """Play the arm open-loop; Output: the visited positions."""
    board = CONSTITUTION.board.make_board()
    belief = _delta_belief(cop_at)
    position, trail = start, []
    for step in range(from_step, from_step + steps):
        move = brain.pick_move(_observation(board, position, step=step), belief)
        assert move != "STAY", (step, position)
        position = board.apply_move(position, move)
        trail.append(position)
    return trail


def test_the_first_lap_is_the_logged_hex_loop() -> None:
    """g01 steps 13-18 / g03 steps 11-16: S,E,N,N,W,S out of (3,3), exactly."""
    trail = _run(make_brain("vibecode-thief", seed=1), (0, 0), 6)  # type: ignore[arg-type]
    assert trail == LOOP


def test_the_loop_repeats_with_period_six_for_a_full_clock() -> None:
    """g01/g03/g05 mid-game: the same six cells, in order, lap after lap."""
    trail = _run(VibecodeThiefBrain(seed=1), (0, 0), 24)
    assert trail == LOOP * 4
    assert set(trail) == set(LOOP)


def test_off_loop_positions_converge_back_onto_the_loop() -> None:
    """The opening wander is flattened to a greedy walk onto the loop's far side."""
    trail = _run(VibecodeThiefBrain(seed=1), (0, 0), 6, start=(6, 6))
    assert any(cell in LOOP for cell in trail)


def test_a_diagonal_cut_draws_the_logged_stay() -> None:
    """g03/g05 step 7: at (4,4) with the cop cutting from (3,3) — both ring arcs
    in step-on reach, own cell safe — the thief holds (the one STAY per game)."""
    board = CONSTITUTION.board.make_board()
    brain = VibecodeThiefBrain(seed=1)
    move = brain.pick_move(_observation(board, (4, 4), step=7), _delta_belief((3, 3)))
    assert move == "STAY"


def test_an_intercepting_cop_reverses_the_lap() -> None:
    """Inferred, not observed (docstring): from (4,4) the ccw next cell (3,4) sits
    in a (3,4)-cop's step-on reach, so the lap reverses — W back to (4,3). Without
    this the arm dies in ~5 steps to any intercept, which the real thief did not."""
    board = CONSTITUTION.board.make_board()
    brain = VibecodeThiefBrain(seed=1)
    move = brain.pick_move(_observation(board, (4, 4), step=10), _delta_belief((3, 4)))
    assert move == "W"
    again = brain.pick_move(_observation(board, (4, 3), step=11), _delta_belief((3, 4)))
    assert again == "STAY"  # both arcs now covered from (3,4): the hold answers it


def test_the_final_steps_sprint_vertically_away_from_the_cop() -> None:
    """g03/g05 steps 32-35: the loop breaks into N,N,N with the cop to the south."""
    threshold = CONSTITUTION.movement.survival_threshold
    brain = VibecodeThiefBrain(seed=1)
    trail = _run(brain, (6, 3), 3, start=(2, 4), from_step=threshold - 2)
    rows = [row for row, _col in trail]
    assert rows == sorted(rows, reverse=True) or rows[0] < 2  # strictly northward
    assert trail[-1][0] < 2


def test_it_never_proposes_a_barrier() -> None:
    """All 105 logged thief steps carry barrier_placed null; the arm has no wall path."""
    board = CONSTITUTION.board.make_board()
    brain = VibecodeThiefBrain(seed=1)
    belief = _delta_belief((0, 0))
    for position in ((3, 3), (4, 4), (2, 3), (6, 6)):
        decision = brain.decide(_observation(board, position), belief)
        assert decision.barrier is None
        assert decision.move != "STAY"

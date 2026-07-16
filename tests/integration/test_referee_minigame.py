"""PRD_engine §8 acceptance: scripted referee-mode mini-games reach all four scored endings.

Composes board + rules + scoring + the shipped config (full-information referee mode,
PLAN §3) — no peer/wire machinery involved. Each script drives both agents move-by-move
and asserts the specific ending and its scoring row.
"""

from pathlib import Path

from copthief_core.domain.board import Board, Coord
from copthief_core.domain.rules import Outcome, check_end, is_legal_barrier, is_legal_move
from copthief_core.domain.scoring import score_mini_game
from copthief_core.shared.config import load_all

CONSTITUTION, _PRIVATE, _LIMITS = load_all(Path("config"), counted=False)


def _play(
    cop_moves: list[str], thief_moves: list[str], barriers: dict[int, Coord]
) -> tuple[Outcome | None, Board, int]:
    """Drive a scripted referee-mode game; returns (outcome, final board, steps played).

    Per step: thief moves, then the cop either moves or places a scripted barrier
    (placing forgoes movement — book ch.3 §3.4). Every scripted action is asserted
    legal before it is applied, so a bad script fails the test loudly.
    """
    movement = CONSTITUTION.movement
    board = CONSTITUTION.board.make_board()
    cop, thief = CONSTITUTION.board.cop_start, CONSTITUTION.board.thief_start
    outcome: Outcome | None = None
    step = 0
    for step, (cop_move, thief_move) in enumerate(
        zip(cop_moves, thief_moves, strict=True), start=1
    ):
        assert is_legal_move(board, thief, thief_move, movement.move_set)
        thief = board.apply_move(thief, thief_move)
        if step in barriers:
            cell = barriers[step]
            assert is_legal_barrier(
                board,
                cop,
                cell,
                barriers_used=len(board.barriers),
                max_barriers=movement.max_barriers,
            )
            board = board.with_barrier(cell)
        else:
            assert is_legal_move(board, cop, cop_move, movement.move_set)
            cop = board.apply_move(cop, cop_move)
        outcome = check_end(
            board,
            cop_pos=cop,
            thief_pos=thief,
            steps_survived=step,
            survival_threshold=movement.survival_threshold,
            max_moves=movement.max_moves,
        )
        if outcome is not None:
            break
    return outcome, board, step


def test_capture_by_landing_ending() -> None:
    # Thief sits at [3,3]; cop walks the diagonal staircase from [0,0] and lands on it.
    cop_moves = ["S", "E", "S", "E", "S", "E"]
    outcome, _, _ = _play(cop_moves, ["STAY"] * len(cop_moves), barriers={})
    assert outcome is Outcome.COP_CAPTURE
    assert score_mini_game(outcome, CONSTITUTION.scoring) == (
        CONSTITUTION.scoring.capture_cop,
        CONSTITUTION.scoring.capture_thief,
    )


def test_capture_by_barrier_ending() -> None:
    # Cop walks next to the stationary thief and drops the barrier on the thief's cell.
    cop_moves = ["S", "E", "S", "E", "S", "STAY"]
    outcome, board, _ = _play(cop_moves, ["STAY"] * 6, barriers={6: (3, 3)})
    assert outcome is Outcome.COP_CAPTURE
    assert (3, 3) in board.barriers


def test_capture_by_imprisonment_ending() -> None:
    # Thief walks into the [6,6] corner (board edges block two sides); cop walks to [5,5]
    # and seals the two open neighbors [5,6] and [6,5] with barriers - imprisonment.
    thief_moves = ["S", "S", "S", "E", "E", "E"] + ["STAY"] * 6
    cop_moves = ["S", "S", "S", "S", "S", "E", "E", "E", "E", "E", "STAY", "STAY"]
    outcome, board, played = _play(cop_moves, thief_moves, barriers={11: (5, 6), 12: (6, 5)})
    assert outcome is Outcome.COP_CAPTURE
    assert played == 12
    assert board.barriers == {(5, 6), (6, 5)}


def test_survival_ending_at_the_threshold() -> None:
    steps = CONSTITUTION.movement.survival_threshold
    outcome, _, played = _play(["STAY"] * steps, ["STAY"] * steps, barriers={})
    assert outcome is Outcome.THIEF_SURVIVAL
    assert played == steps
    assert score_mini_game(outcome, CONSTITUTION.scoring) == (
        CONSTITUTION.scoring.survival_cop,
        CONSTITUTION.scoring.survival_thief,
    )

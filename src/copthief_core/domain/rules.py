"""Game rules (book ch.3 §3.4–3.5): action legality, the barrier law, capture, end states.

One rules module serves both orchestration modes (PLAN §3): referee mode calls these with
both true positions (tests/arena/tuning); peer mode calls them with our position and the
opponent's *claims*, deferring truth to commit-reveal + the audit. Physics is enforced by
the agents themselves — every inbound action is validated with the same functions that
validate our own (PRD_engine E-2).
"""

from __future__ import annotations

from enum import Enum

from copthief_core.domain.board import Board, Coord


class Outcome(Enum):
    """Terminal result of a mini-game (scoring table, book ch.3 table 2)."""

    COP_CAPTURE = "cop_capture"
    THIEF_SURVIVAL = "thief_survival"
    TECHNICAL_LOSS = "technical_loss"


def legal_moves(board: Board, pos: Coord, move_set: tuple[str, ...]) -> tuple[str, ...]:
    """The subset of the signed `move_set` playable from `pos` (destination not blocked)."""
    return tuple(m for m in move_set if not board.is_blocked(board.apply_move(pos, m)))


def is_legal_move(board: Board, pos: Coord, move: str, move_set: tuple[str, ...]) -> bool:
    """True iff `move` is in the signed move set AND its destination is not blocked.

    Moves outside the orthogonal alphabet (diagonals, typos) are simply illegal here —
    peer mode treats them as a protocol violation rather than raising.
    """
    if move not in move_set:
        return False
    return not board.is_blocked(board.apply_move(pos, move))


def is_legal_barrier(
    board: Board, cop_pos: Coord, cell: Coord, *, barriers_used: int, max_barriers: int
) -> bool:
    """The barrier law: quota unspent, cell is the cop's own or an orthogonal neighbor,
    in bounds, and not already barricaded (placement is irreversible, so never doubled)."""
    if barriers_used >= max_barriers:
        return False
    if cell != cop_pos and cell not in board.neighbors(cop_pos):
        return False
    return not board.is_blocked(cell)


def is_imprisoned(board: Board, pos: Coord) -> bool:
    """True iff every orthogonal escape from `pos` is blocked (barrier or board edge).

    STAY does not rescue an imprisoned thief — the book defines imprisonment purely by
    blocked neighbors (PRD_engine §6.3).
    """
    return all(board.is_blocked(n) for n in board.neighbors(pos))


def check_end(
    board: Board,
    *,
    cop_pos: Coord,
    thief_pos: Coord,
    steps_survived: int,
    survival_threshold: int,
    max_moves: int,
) -> Outcome | None:
    """Referee-mode end-of-mini-game resolution; None while the game continues.

    Capture is checked before survival (a capture on the threshold step is a capture).
    The three capture forms (PRD_engine E-4): cop landed on the thief, a barrier sits on
    the thief's cell, or the thief is imprisoned. Reaching `survival_threshold` valid
    steps — or the `max_moves` cap with no capture — is thief survival (an uncaught
    thief at the cap has, by definition, outlasted the pursuit). TECHNICAL_LOSS is never
    produced by physics; the protocol layer assigns it.
    """
    if cop_pos == thief_pos or thief_pos in board.barriers or is_imprisoned(board, thief_pos):
        return Outcome.COP_CAPTURE
    if steps_survived >= survival_threshold or steps_survived >= max_moves:
        return Outcome.THIEF_SURVIVAL
    return None

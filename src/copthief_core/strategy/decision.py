"""The Decision seam (TODO M5-2; PRD_police_brain §3): one turn's action, move XOR barrier.

A barrier turn keeps position — reference `MoveType.BARRIER` semantics (@960499fd,
ADR-0002 behavior mirror): the mover forgoes its step to wall a cell. The clamp
helpers here are the single legality funnel every brain's proposal passes through
(never an illegal action out of the seam, never a stalled loop).
"""

from __future__ import annotations

from dataclasses import dataclass

from copthief_core.domain.board import STAY, Board, Coord
from copthief_core.domain.rules import is_legal_barrier, legal_moves

# The sealed-record move value for a wall turn (our own alphabet — self-consistent per
# side; the audit re-hashes bytes, not grammar. The reference seals "BARRIER:<dir>").
BARRIER_MOVE = "BARRIER"


@dataclass(frozen=True)
class Decision:
    """One turn's chosen action: a move, or a barrier placement (position unchanged).

    `hint_verdict`/`hint_landmark` are the M5-3 hint-intent seam: the brain may ask
    the verbal layer to lie toward a chosen decoy (the M3-4 mechanism's policy input).
    None means the truthful default; the sealed intent always matches the verdict.

    `landing_confidence` is the M13 claim-intent seam (ADR-0016): the brain's own
    P(opponent on the cell this move lands on), priced from the SAME posterior it
    hunted — the claim gate's input. None = unpriced; the emitter falls back to the
    raw belief (every non-PoliceBrain brain, and every degrade path).
    """

    move: str = STAY
    barrier: Coord | None = None
    hint_verdict: str | None = None
    hint_landmark: str | None = None
    landing_confidence: float | None = None

    def __post_init__(self) -> None:
        if self.barrier is not None and self.move != STAY:
            raise ValueError("a barrier turn moves nothing — move must be STAY")
        if self.hint_landmark is not None and self.hint_verdict is None:
            raise ValueError("a hint landmark needs a hint verdict")
        if self.barrier is not None and self.landing_confidence is not None:
            raise ValueError("a wall turn lands nowhere — it cannot price a landing")


def clamp_move(board: Board, position: Coord, move_set: tuple[str, ...], proposal: str) -> str:
    """`proposal` if legal, else the first sorted legal move, else STAY (never stall)."""
    candidates = sorted(legal_moves(board, position, move_set))
    if not candidates:
        return STAY
    return proposal if proposal in candidates else candidates[0]


def barrier_is_playable(
    board: Board, position: Coord, role: str, cell: Coord, *, used: int, quota: int
) -> bool:
    """The barrier law gate for a proposal: police-only, quota unspent, cell in reach."""
    if role != "police":
        return False
    return is_legal_barrier(board, position, cell, barriers_used=used, max_barriers=quota)

"""Turn sealing (book ch.5 §5.3; PRD_crypto §4): build the self-consistent sealed record.

The record's key set is self-only (kit §3): the opponent never reconstructs it, only
re-hashes what we reveal — so seal↔store↔reveal must be byte-identical, which is why the
record is built exactly once, here, and stored verbatim.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from copthief_core.domain.board import Coord
from copthief_core.domain.crypto import commit as crypto_commit
from copthief_core.domain.crypto import make_nonce


def state_string(grid_size: int, position: Coord, barriers: frozenset[Coord]) -> str:
    """The reference's exact self-state encoding, pinned by the kit vectors (kit §3).

    Micro-snippet transplant (ADR-0002 log): the format — Python list repr WITH the
    space after the comma, barriers sorted — must reproduce byte-for-byte, or our own
    revealed records would not match the form other tooling expects.
    """
    barrier_lists = sorted([list(b) for b in barriers])
    return f"grid={grid_size}x{grid_size};self={list(position)};barriers={barrier_lists}"


@dataclass(frozen=True)
class SealedTurn:
    """One sealed record: the verbatim payload, its withheld nonce, the sent commit."""

    payload: dict[str, Any]
    nonce: str
    commit: str


def seal_turn(
    *,
    step: int,
    grid_size: int,
    position: Coord,
    barriers: frozenset[Coord],
    move: str,
    intent: str,
    hint: str,
) -> SealedTurn:
    """Seal one turn (Input: the turn's facts; Output: record + nonce + commit).

    The nonce is fresh per record (`secrets`) and withheld until the end-of-game audit;
    only the commit travels with the TurnMessage. Richer fields (verdict, sub_game,
    role, timing, tokens) join the payload when their features land (M3+, PRD_crypto §4).
    """
    payload: dict[str, Any] = {
        "step": step,
        "state": state_string(grid_size, position, barriers),
        "position": list(position),
        "move": move,
        "intent": intent,
        "hint": hint,
    }
    nonce = make_nonce()
    return SealedTurn(payload=payload, nonce=nonce, commit=crypto_commit(payload, nonce))

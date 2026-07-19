"""Post-audit opponent profiling (TODO M5-5; PLAN §8 audit tail; PRD_police_brain §6).

A verified audit reveals the opponent's sealed truth: per-turn intent labels
(truth/lie — reference constants) and the actual move trail. This module turns that
into a per-opponent profile (lie-rate, motion prior) and shifts the NEXT mini-game's
hint trust through config-owned values only — the belief math itself is untouched
(M3-8 boundary), and the shift is floored: distrust-but-never-eliminate (SQ3 stance).
Scent honesty is deliberately NOT profiled — transmitted grids are never sealed (SQ3),
so the audit carries no scent ground truth to measure against.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from copthief_core.strategy.hints import VERDICT_LIE


@dataclass(frozen=True)
class OpponentProfile:
    """What the audits so far prove about one opponent's play."""

    games: int
    hints: int
    lies: int
    moves: dict[str, int]

    @property
    def lie_rate(self) -> float:
        """Fraction of sealed hints labeled a lie (0.0 before any evidence)."""
        return self.lies / self.hints if self.hints else 0.0

    @property
    def motion_prior(self) -> dict[str, float]:
        """Normalized distribution over the opponent's revealed moves."""
        total = sum(self.moves.values())
        return {move: count / total for move, count in self.moves.items()} if total else {}


def profile_records(records: Iterable[Mapping[str, Any]]) -> OpponentProfile:
    """One audited mini-game's profile from its revealed records (wire dicts).

    Only game records count (step ≥ 1 — the reference's step-0 system_spec record
    carries no play evidence); every game record seals exactly one hint + intent.
    """
    hints = lies = 0
    moves: dict[str, int] = {}
    for record in records:
        payload = record["payload"]
        step = payload.get("step")
        if not isinstance(step, int) or step < 1:
            continue
        hints += 1
        if payload.get("intent") == VERDICT_LIE:
            lies += 1
        move = str(payload.get("move"))
        moves[move] = moves.get(move, 0) + 1
    return OpponentProfile(games=1, hints=hints, lies=lies, moves=moves)


def merge_profiles(first: OpponentProfile, second: OpponentProfile) -> OpponentProfile:
    """Accumulate evidence across mini-games (a series profiles per opponent)."""
    moves = dict(first.moves)
    for move, count in second.moves.items():
        moves[move] = moves.get(move, 0) + count
    return OpponentProfile(
        games=first.games + second.games,
        hints=first.hints + second.hints,
        lies=first.lies + second.lies,
        moves=moves,
    )


def shifted_hint_trust(profile: OpponentProfile, *, base: float, floor: float) -> float:
    """The next mini-game's hint trust: scaled by proven honesty, never below the
    config floor (`[belief] profile_hint_floor`) — hints stay admissible evidence."""
    return max(floor, base * (1.0 - profile.lie_rate))

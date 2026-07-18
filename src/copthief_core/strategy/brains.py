"""BrainBase seam + baseline brains (TODO M3-5; PLAN §8; App E rule 25).

The seam the M5 role brains implement: `_pick_move(observation, belief) -> move`.
Moves are ALWAYS pure Python — no LLM ever decides one. The public template method
clamps every proposal to legality: an illegal pick degrades to the first sorted legal
move (deterministic), a fully-walled position degrades to STAY (never stall — the
audit resolves the imprisonment). Baselines here are the arena floor: seeded random,
and greedy-Manhattan over the belief argmax. Barrier placement/claim policy are M5
(claims are automatic per SQ2; barriers need the belief-mass surgery of PoliceBrain).
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import STAY, Board, Coord
from copthief_core.domain.rules import legal_moves


@dataclass(frozen=True)
class Observation:
    """What a brain may see: OUR truth + the signed alphabet — never the opponent's."""

    board: Board
    position: Coord
    move_set: tuple[str, ...]
    role: str
    step: int


class BrainBase(ABC):
    """The strategy seam (Input: seed for reproducible play; see pick_move)."""

    def __init__(self, *, seed: int) -> None:
        self._rng = random.Random(seed)

    def pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        """Template method: delegate to `_pick_move`, then clamp to legality."""
        candidates = sorted(
            legal_moves(observation.board, observation.position, observation.move_set)
        )
        if not candidates:
            return STAY
        proposal = self._pick_move(observation, belief)
        return proposal if proposal in candidates else candidates[0]

    @abstractmethod
    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        """The strategy core — may propose freely; the template clamps."""


class RandomBrain(BrainBase):
    """Uniform seeded choice over the legal moves (the M1 skeleton walk, seam-shaped)."""

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        candidates = sorted(
            legal_moves(observation.board, observation.position, observation.move_set)
        )
        return self._rng.choice(candidates) if candidates else STAY


class GreedyManhattanBrain(BrainBase):
    """Chase (police) or flee (thief) the belief argmax by Manhattan distance.

    Deterministic: ties break on the sorted move order. Reads the belief through its
    public surface only (PRD_belief §7).
    """

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        target = belief.argmax()
        candidates = sorted(
            legal_moves(observation.board, observation.position, observation.move_set)
        )
        if not candidates:
            return STAY

        def distance_after(move: str) -> int:
            dest = observation.board.apply_move(observation.position, move)
            return abs(dest[0] - target[0]) + abs(dest[1] - target[1])

        if observation.role == "police":
            return min(candidates, key=lambda m: (distance_after(m), m))
        return max(candidates, key=lambda m: (distance_after(m), [-ord(ch) for ch in m]))


def make_brain(name: str, *, seed: int) -> BrainBase:
    """Config-name factory (`game.toml [strategy]`): 'random' | 'greedy-manhattan'."""
    if name == "random":
        return RandomBrain(seed=seed)
    if name == "greedy-manhattan":
        return GreedyManhattanBrain(seed=seed)
    raise ValueError(f"unknown brain: {name!r}")

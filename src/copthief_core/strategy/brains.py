"""BrainBase seam + baseline brains (TODO M3-5/M5-2; PLAN §8; App E rule 25).

The seam the role brains implement: `_pick_move` (move-only policies) and/or `_decide`
(move-or-barrier, PRD_police_brain §3). Moves are ALWAYS pure Python — no LLM ever
decides one. The public template methods clamp every proposal to legality: an illegal
move degrades to the first sorted legal move, an illegal/over-quota/off-role barrier
degrades to the clamped `_pick_move`, a fully-walled position degrades to STAY (never
stall — the audit resolves the imprisonment). `options` carries private config knobs
(`game.toml [strategy.*]` / `config/arena.json`) — quantitative values never live here.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field, replace

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import STAY, Board, Coord
from copthief_core.domain.gazetteer import Gazetteer
from copthief_core.domain.rules import legal_moves
from copthief_core.shared.config_model import PheromoneParams
from copthief_core.strategy.decision import Decision, barrier_is_playable, clamp_move


@dataclass(frozen=True)
class Observation:
    """What a brain may see: OUR truth + the signed alphabet — never the opponent's.

    The M5-3 deception kit rides here: the (public) gazetteer, OUR OWN transmitted
    scent so far (`own_smell` — exactly the evidence the opponent has received from
    us), and the signed pheromone params — everything a self-mirror needs, nothing
    about the opponent's truth. The signed clock (`survival_threshold`/`max_moves`)
    lets brains anchor time-shaped knobs to the constitution instead of copying it
    into private config (0 = unknown, legacy callers unchanged).
    """

    board: Board
    position: Coord
    move_set: tuple[str, ...]
    role: str
    step: int
    barriers_used: int = 0
    max_barriers: int = 0
    survival_threshold: int = 0
    max_moves: int = 0
    gazetteer: Gazetteer | None = None
    own_smell: dict[str, float] = field(default_factory=dict)
    pheromones: PheromoneParams | None = None


class BrainBase(ABC):
    """The strategy seam (Input: seed for reproducible play + private config options)."""

    def __init__(self, *, seed: int, options: Mapping[str, float] | None = None) -> None:
        self._rng = random.Random(seed)
        self._options: Mapping[str, float] = dict(options or {})

    def pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        """Move-only template method: delegate to `_pick_move`, then clamp to legality."""
        return clamp_move(
            observation.board,
            observation.position,
            observation.move_set,
            self._pick_move(observation, belief),
        )

    def decide(self, observation: Observation, belief: BeliefFilter) -> Decision:
        """Full-action template method: `_decide`, barrier law enforced, moves clamped,
        hint-intent fields preserved verbatim (the clamp governs actions, not talk)."""
        proposal = self._decide(observation, belief)
        if proposal.barrier is not None:
            if barrier_is_playable(
                observation.board,
                observation.position,
                observation.role,
                proposal.barrier,
                used=observation.barriers_used,
                quota=observation.max_barriers,
            ):
                return replace(proposal, move=STAY)
            return replace(proposal, barrier=None, move=self.pick_move(observation, belief))
        return replace(
            proposal,
            move=clamp_move(
                observation.board, observation.position, observation.move_set, proposal.move
            ),
        )

    @abstractmethod
    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        """The move-policy core — may propose freely; the template clamps."""

    def _decide(self, observation: Observation, belief: BeliefFilter) -> Decision:
        """The full-action core; the default wraps `_pick_move` (baselines never wall)."""
        return Decision(move=self._pick_move(observation, belief))


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


def make_brain(name: str, *, seed: int, options: Mapping[str, float] | None = None) -> BrainBase:
    """Config-name factory (`game.toml [strategy]` / `config/arena.json` rosters).

    Core names: 'random' | 'greedy-manhattan' | 'ref-police' | 'ref-thief' |
    'belief-evader'. A spec with a colon is the book §6.2 dotted notation
    `package.module:Class` — the role packages' door into the arena and the peer
    loop; core itself stays role-blind.
    """
    from copthief_core.strategy.best2934_cop import Best2934CopBrain
    from copthief_core.strategy.best2934_thief import Best2934ThiefBrain
    from copthief_core.strategy.doctrine_evader import DoctrineEvaderBrain
    from copthief_core.strategy.evader_brains import BeliefEvaderBrain
    from copthief_core.strategy.hunter_cop import HunterCopBrain
    from copthief_core.strategy.nisyar1_thief import NisYar1ThiefBrain
    from copthief_core.strategy.reference_brains import RefPoliceBrain, RefThiefBrain
    from copthief_core.strategy.vibecode_cop import VibecodeCopBrain
    from copthief_core.strategy.vibecode_thief import VibecodeThiefBrain

    core: dict[str, type[BrainBase]] = {
        "random": RandomBrain,
        "greedy-manhattan": GreedyManhattanBrain,
        "ref-police": RefPoliceBrain,
        "ref-thief": RefThiefBrain,
        "belief-evader": BeliefEvaderBrain,
        "doctrine-evader": DoctrineEvaderBrain,
        "best2934-police": Best2934CopBrain,
        "best2934-thief": Best2934ThiefBrain,
        "vibecode-police": VibecodeCopBrain,
        "vibecode-thief": VibecodeThiefBrain,
        "hunter-cop": HunterCopBrain,
        "nisyar1-thief": NisYar1ThiefBrain,
    }
    if name in core:
        return core[name](seed=seed, options=options)
    if ":" in name:
        import importlib

        module_name, _, class_name = name.partition(":")
        cls = getattr(importlib.import_module(module_name), class_name)
        if not (isinstance(cls, type) and issubclass(cls, BrainBase)):
            raise ValueError(f"{name!r} is not a BrainBase subclass")
        return cls(seed=seed, options=options)
    raise ValueError(f"unknown brain: {name!r}")

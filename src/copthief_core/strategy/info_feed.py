"""Belief information feeds — the wire-shape seam (referee mode; kit issue #6).

One rules loop, two information structures. Under the `reference-v3` wire positions
stay hidden: a belief advances only on the opponent's transmitted locked-model trail
(ScentFeed — the historical referee seam, unchanged). Under the `bookletter-v3` wire
each step's Reveal makes the opponent's position computable from the signed start, so
every decision is taken under common knowledge (TruthFeed — a certainty delta at the
revealed cell). The A/B powers the committed wire-shape balance table
(`scripts/balance_run.py`), decision support for the joint wire-shape ADR.
"""

from __future__ import annotations

from typing import Protocol

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import Board, Coord
from copthief_core.domain.scent import ScentField
from copthief_core.shared.config_model import Constitution


class BeliefFeed(Protocol):
    """Per-half-turn belief update: what the wire lets an agent learn about its rival."""

    def observe(
        self, belief: BeliefFilter, *, trail: ScentField, truth: Coord, board: Board
    ) -> BeliefFilter:
        """Advance `belief` after the opponent acted; returns the filter brains use."""
        ...


class ScentFeed:
    """The hidden-position wire (reference-v3): the trail is the only channel."""

    def observe(
        self, belief: BeliefFilter, *, trail: ScentField, truth: Coord, board: Board
    ) -> BeliefFilter:
        """Motion-predict, then weigh the opponent's transmitted trail (in place —
        byte-identical to the pre-seam referee loop; `truth` is deliberately unread)."""
        belief.predict()
        belief.update_scent(trail.snapshot())
        return belief


class TruthFeed:
    """The common-knowledge wire (bookletter-v3): per-step Reveal collapses belief."""

    def __init__(self, constitution: Constitution, *, smell_trust: float) -> None:
        self._move_set = constitution.movement.move_set
        self._center = constitution.pheromones.center_intensity
        self._decay = constitution.pheromones.decay
        self._smell_trust = smell_trust

    def observe(
        self, belief: BeliefFilter, *, trail: ScentField, truth: Coord, board: Board
    ) -> BeliefFilter:
        """A fresh certainty delta at the revealed cell, on the CURRENT board (declared
        barriers included) — brains read only the filter, so every brain becomes
        full-information without any brain change."""
        return BeliefFilter(
            board=board,
            move_set=self._move_set,
            start=truth,
            center_intensity=self._center,
            decay=self._decay,
            smell_trust=self._smell_trust,
            hint_trust=0.0,
        )

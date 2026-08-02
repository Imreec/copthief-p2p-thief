"""Sealing-cop arena arms (TODO M7-30; PRD_thief_brain §2 threat model) — ⚑ thief repo.

Opponent MODELS for the tuning instrument, never our agent and never a role brain: they
enter the POLICE side of a roster the way `ref-police` does. The tactic they model is the
one the 2026-08-01 warm-up lost s1/s3/s5 to — a cop that walks up to a camped thief and
spends two of its fourteen barriers on a corner's two gates, which App E rules 46-47
score as a capture.

Why a new arm was needed at all: nothing in the shipped roster applies sealing pressure.
`ref-police` walls the cell of the step it would have taken, so every barrier it places
costs it the advance that would have closed the distance — measured, it self-neuters
(at a barrier chance of 0.7 or 1.0 our thief survives 32/32). Across the whole shipped
pool the referee resolved ONE barrier capture and ZERO imprisonments in 224 games, so a
GA run over that pool could not price anti-sealing behaviour at any weight.

Both arms are config-gated and INERT by default: with no `seal_max_exits` option they are
plain belief chasers, so naming one in a roster changes nothing until a config asks for
sealing. Deterministic, no RNG, options-only knobs (quantitative values never live here).
"""

from __future__ import annotations

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import STAY, Coord
from copthief_core.domain.rules import legal_moves
from copthief_core.strategy.brains import BrainBase, Observation
from copthief_core.strategy.decision import Decision

__all__ = ["BarrierCapturePoliceBrain", "SealerPoliceBrain"]


def _manhattan(a: Coord, b: Coord) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class SealerPoliceBrain(BrainBase):
    """Chase the belief argmax; wall an escape gate of a nearly-enclosed believed cell.

    Input: the standard police Observation + belief, and `seal_max_exits` (the open-exit
    count at or below which a believed cell is worth sealing — 2 is a corner, 3 an edge).
    Output: a Decision that either walls one gate or takes the chasing step.

    The believed cell itself is never walled: that is the rule-46 capture form, a
    different tactic, and modelling it here would make the arm an oracle rather than the
    thing we watched happen. `BarrierCapturePoliceBrain` keeps it as a disclosed bracket.
    """

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        target = belief.argmax()
        candidates = sorted(
            legal_moves(observation.board, observation.position, observation.move_set)
        )
        if not candidates:
            return STAY
        return min(
            candidates,
            key=lambda m: (
                _manhattan(observation.board.apply_move(observation.position, m), target),
                m,
            ),
        )

    def _gates(self, observation: Observation, target: Coord) -> list[Coord]:
        """The believed cell's open exits that this cop may legally barricade now."""
        board = observation.board
        exits = [cell for cell in board.neighbors(target) if not board.is_blocked(cell)]
        if not exits or len(exits) > self._options.get("seal_max_exits", 0.0):
            return []
        reach = {observation.position, *board.neighbors(observation.position)}
        return sorted(cell for cell in exits if cell in reach)

    def _decide(self, observation: Observation, belief: BeliefFilter) -> Decision:
        target = belief.argmax()
        quota_left = observation.barriers_used < observation.max_barriers
        if quota_left and target != observation.position:
            gates = self._gates(observation, target)
            if gates:
                return Decision(barrier=gates[0])
        return Decision(move=self._pick_move(observation, belief))


class BarrierCapturePoliceBrain(SealerPoliceBrain):
    """The disclosed BRACKET: also wall the believed cell itself when the law allows.

    Not a model of an observed opponent — it is the upper bound on what a barrier-using
    cop with a good belief could do, kept so the evidence can state how far the threat
    class reaches. It is a yardstick, never a GA pool member: tuning against an arm that
    converts every correct belief into a capture would price nothing else.
    """

    def _decide(self, observation: Observation, belief: BeliefFilter) -> Decision:
        board = observation.board
        target = belief.argmax()
        reach = {observation.position, *board.neighbors(observation.position)}
        if (
            observation.barriers_used < observation.max_barriers
            and target in reach
            and not board.is_blocked(target)
        ):
            return Decision(barrier=target)
        return super()._decide(observation, belief)

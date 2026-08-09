"""vibecode's thief as an arena arm (M9 study) — modeled from audit-revealed play.

Their repos are PRIVATE, so unlike the best2934/uoh-sqak arms this is not modeled
from source: it is reconstructed from the `opponent_records` of anrbj666's archived
counted series against them (anrbj666 won 75-35), where every audited step reveals
the thief's sealed position and move:

    P2P-Police/results/log_anrbj666-vs-vibecode_g01.json  (13 steps, captured)
    P2P-Police/results/log_anrbj666-vs-vibecode_g03.json  (13 steps, captured)
    P2P-Police/results/log_anrbj666-vs-vibecode_g05.json  (35 steps, survived)

Observed policy, identical in shape across all three games: from the center start
march S to the south edge (steps 1-3), run along the edge to a corner — east to the
(6,6) corner in g01/g03, west to (6,0) in g05, so the pick is input-dependent and
modeled here as fleeing the believed cop's half of the board — then oscillate between
the corner and its edge neighbor until the clock ends. It never STAYs and never
proposes a barrier. Its hints were truthful move-echoes ("moving s"); hints are the
verbal layer's business, not a brain's, so only movement is modeled.

Fidelity is a BEHAVIORAL APPROXIMATION, not a port: the phase is re-derived from the
observed position every turn (no hidden state), the corner rule is our best inference
from a 2-of-3 / 1-of-3 split, and a blocked scripted move degrades through the
template clamp rather than reproducing whatever their unseen code would do. The
policy has no free quantitative parameters — every target is board geometry — so
there is no options table to override.
"""

from __future__ import annotations

from copthief_core.domain.belief import BeliefFilter
from copthief_core.domain.board import Board
from copthief_core.strategy.brains import BrainBase, Observation

__all__ = ["VibecodeThiefBrain"]


def _south_row(board: Board) -> int:
    """The edge row the observed thief always ran to (max row under top-left axes)."""
    return board.axis_start_index + board.grid_size - 1


def _corner_pick(board: Board, belief: BeliefFilter) -> int:
    """The target corner's column: the one on the far side from the believed cop.

    g01/g03 ran east with the cop opening from the west column; g05 ran west. The
    logs cannot reveal their belief, so the modeled rule is the simplest consistent
    one: flee the believed cop's half of the board, east on the exact-center tie.
    """
    low = board.axis_start_index
    high = _south_row(board)
    peak_col = belief.argmax()[1]
    return low if peak_col * 2 > low + high else high


class VibecodeThiefBrain(BrainBase):
    """South-edge corner oscillator (their audit-revealed thief).

    Input:  the observation and our belief over the cop's cell.
    Output: the scripted move for the current phase — S off the edge, along the edge
            toward the picked corner, and the endless corner<->neighbor oscillation
            once there. Never STAY, never a barrier; the template clamps a blocked
            scripted move to the first sorted legal move.
    """

    def _pick_move(self, observation: Observation, belief: BeliefFilter) -> str:
        board = observation.board
        row, col = observation.position
        if row != _south_row(board):
            return "S"
        corner_col = _corner_pick(board, belief)
        if col == corner_col:
            # At the corner the observed thief always stepped back toward mid-edge.
            return "E" if corner_col == board.axis_start_index else "W"
        return "W" if corner_col < col else "E"

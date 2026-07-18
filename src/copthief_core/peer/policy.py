"""M1 skeleton policy: seeded geometric play + template hints.

Deliberately brainless — the M1 walking skeleton needs *legal, deterministic* play to
exercise sealing/audit end-to-end, nothing more. The BrainBase seam replaces this at
M3-5 (baselines) and M5 (role brains); the LLM never decides moves at any milestone
(App E rule 25). `random` here is game variety, not cryptography — nonces come from
`secrets` in domain.crypto.
"""

from __future__ import annotations

import random

from copthief_core.domain.board import STAY, Board, Coord
from copthief_core.domain.rules import legal_moves

# ≤ the App F hint word-cap example (15) by construction; M3 replaces these with the
# gazetteer template bank wired to map_area landmarks.
_HINT_BANK = (
    "Somewhere the lamps are dim.",
    "I drift with the crowd.",
    "The alleys know my name.",
    "Listen for footsteps, not words.",
)


class SkeletonPolicy:
    """Seeded random-legal walk + cycling template hints (M1 only)."""

    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)
        self._hint_index = 0

    def pick_move(self, board: Board, pos: Coord, move_set: tuple[str, ...]) -> str:
        """A uniformly random *legal* move; sorted candidates keep seeds reproducible.

        With opponent barriers noted since M3-3, a fully-walled position can leave no
        legal move — never stall the loop (the reference falls back to HOLD): STAY,
        and let the audit/rules layer resolve the imprisonment.
        """
        candidates = sorted(legal_moves(board, pos, move_set)) or [STAY]
        return self._rng.choice(candidates)

    def next_hint(self, *, hint_max_words: int) -> str:
        """The next template hint, truncated to the signed word cap."""
        hint = _HINT_BANK[self._hint_index % len(_HINT_BANK)]
        self._hint_index += 1
        return " ".join(hint.split()[:hint_max_words])

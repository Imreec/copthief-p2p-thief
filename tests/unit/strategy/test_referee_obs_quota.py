"""M7-31: the referee's thief Observation carries the barrier quota (wire parity).

The M7-30 probe (thief repo, PR #61 there) found ThiefBrain's whole trap branch dead
in the referee: `thief_observation` filled neither `barriers_used` nor `max_barriers`,
so the quota gate read `0 < 0` — while the wire (`peer/turns.py`) fills both and the
gate always fires. Every referee number tuned or gated a thief we do not field
(M7-21's headline gene was unmeasurable drift). These pins hold the two builders to
the peer path's exact semantics: quota from the constitution, `barriers_used` = the
agent's OWN placement count (a thief never places — 0; a cop owns every board barrier).
"""

from pathlib import Path

from copthief_core.domain.board import Board
from copthief_core.shared.config import load_all
from copthief_core.strategy.referee_obs import police_observation, thief_observation
from copthief_core.strategy.referee_setup import referee_trail

CONSTITUTION, _PRIVATE, _LIMITS = load_all(Path("config"), counted=False)


def _board() -> Board:
    return CONSTITUTION.board.make_board()


def test_thief_observation_carries_the_wire_barrier_quota() -> None:
    observation = thief_observation(
        CONSTITUTION,
        board=_board(),
        position=CONSTITUTION.board.thief_start,
        step=1,
        trail=referee_trail(CONSTITUTION),
        gazetteer=None,
    )
    assert observation.max_barriers == CONSTITUTION.movement.max_barriers
    assert observation.barriers_used == 0  # the thief's OWN count — it never places
    # The gate that was dead in the instrument (thief brain.py: used < max) now fires
    # exactly as it does on the wire (peer/turns.py fills the same two fields).
    assert observation.barriers_used < observation.max_barriers


def test_police_observation_quota_semantics_unchanged() -> None:
    board = _board().with_barrier((0, 1))
    observation = police_observation(
        CONSTITUTION,
        board=board,
        position=CONSTITUTION.board.cop_start,
        step=2,
        trail=referee_trail(CONSTITUTION),
    )
    assert observation.max_barriers == CONSTITUTION.movement.max_barriers
    assert observation.barriers_used == 1  # every board barrier is the cop's own

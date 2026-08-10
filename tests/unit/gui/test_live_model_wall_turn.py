"""Live view-model wall-turn fold (M10) — a BARRIER decision keeps position.

Latent until containment armed: a wall turn's sealed/logged decision move is
`BARRIER` (reference semantics — the mover forgoes its step), and the fold ran
every decision through `apply_move`, which raises on any non-compass move. No
committed fixture game ever walled, so the crash waited for the first real
placement — surfaced by the M10 fold test the moment `contain_enabled` armed
the local minigame. Split file: `test_live_model.py` sits at the 150-line rule.
"""

from pathlib import Path

from copthief_core.gui.models.live import LiveViewModel
from copthief_core.shared.config import load_all
from copthief_core.strategy.decision import BARRIER_MOVE

CONSTITUTION, _PRIVATE, _LIMITS = load_all(Path("config"), counted=False)


def _model() -> LiveViewModel:
    return LiveViewModel(
        role="police",
        board=CONSTITUTION.board.make_board(),
        start=CONSTITUTION.board.cop_start,
    )


def test_a_wall_turn_decision_keeps_the_position() -> None:
    model = _model()
    start = model.state().own_position
    model.apply(
        {
            "event": "decision",
            "sender": "police",
            "payload": {"brain": "PoliceBrain", "intent": "truth", "move": BARRIER_MOVE, "step": 4},
        }
    )
    view = model.state()
    assert view.own_position == start  # the mover forgoes its step to wall
    assert view.step == 4  # the turn still advances the step counter


def test_a_compass_decision_still_moves() -> None:
    model = _model()
    start = model.state().own_position
    model.apply(
        {
            "event": "decision",
            "sender": "police",
            "payload": {"brain": "PoliceBrain", "intent": "truth", "move": "S", "step": 1},
        }
    )
    assert model.state().own_position == (start[0] + 1, start[1])

"""The 2026-08-07 uoh-sqak loss, pinned so it cannot come back (M7-46) — ⚑ thief repo.

`SqakApexPoliceBrain` in a roster plays OUR turn law (move XOR wall) and, measured that
way, captures nothing — `docs/evidence/m7-46-sqak-arena.md`. The live cop is lethal
because it does BOTH in one turn: the friendly's wire shows a barrier on 13 of 14 turns
while their cop walked (0,0) -> (0,4), and under that tempo the same objective took every
thief sub-game. This harness therefore drives their policy at THEIR tempo — the only
faithful model of the game we actually lost — and pins the two facts that matter:

  * the pre-M7-46 thief is captured on the SIGNED start (the start every counted game
    uses), reproducing the friendly's g02/g04/g06 ending;
  * the shipped thief, with the siege response live, survives the full clock.

Keyless and offline: no opponent, no window, no network. `siege_min_walls` above the
barrier quota provably never fires, so `thief-siege-off` IS the pre-M7-46 brain.
"""

import tomllib
from pathlib import Path

import pytest

from copthief_core.domain.rules import Outcome, check_end
from copthief_core.shared.config_model import Constitution
from copthief_core.strategy.info_feed import ScentFeed
from copthief_core.strategy.referee_obs import police_observation, thief_observation
from copthief_core.strategy.referee_setup import referee_belief, referee_trail
from copthief_thief.brain import ThiefBrain
from copthief_thief.sqak_apex import SqakApexPoliceBrain

CONFIG = Path(__file__).resolve().parents[2] / "config"
SMELL_TRUST = 4.0  # the shipped [belief] smell_trust_weight; the harness is not the agent
# Their PRE-d07b654 build: a wall cost nothing, so any wall deleting one cell was taken.
# This harness reproduces a game already played, so it must model the cop that played it,
# not the one they field now (`APEX_DEFAULTS`, retuned when the Barrier Law was fixed).
PRE_FIX_COP = {"apex_min_gain": 1.0, "apex_barrier_cost": 0.0}


@pytest.fixture(scope="module")
def constitution() -> Constitution:
    from copthief_core.sdk.simulation import SimulationSdk

    return SimulationSdk(CONFIG).constitution


def deployed_options() -> dict[str, float]:
    """The weights `config/game.toml` actually fields, so the pin tracks the agent."""
    table = tomllib.loads((CONFIG / "game.toml").read_text(encoding="utf-8"))
    return {k: float(v) for k, v in table["strategy"]["thief"].items() if isinstance(v, int | float)}


def play_at_live_tempo(constitution: Constitution, thief_brain: ThiefBrain) -> tuple[Outcome, int]:
    """One mini-game where the cop MOVES AND WALLS every turn (their turn law)."""
    board = constitution.board.make_board()
    threshold = constitution.movement.survival_threshold
    intensity = constitution.pheromones.center_intensity
    thief, cop = constitution.board.thief_start, constitution.board.cop_start
    cop_brain = SqakApexPoliceBrain(seed=1, options=PRE_FIX_COP)
    belief = referee_belief(constitution, start=cop, smell_trust=SMELL_TRUST)
    thief_trail, cop_trail, feed = referee_trail(constitution), referee_trail(constitution), ScentFeed()

    for step in range(1, min(threshold, constitution.movement.max_moves) + 1):
        decision = thief_brain.decide(
            thief_observation(constitution, board=board, position=thief, step=step,
                              trail=thief_trail, gazetteer=None),
            belief,
        )
        thief = board.apply_move(thief, decision.move)
        thief_trail.advance(thief, intensity)
        ending = check_end(board, cop_pos=cop, thief_pos=thief, steps_survived=step,
                           survival_threshold=threshold, max_moves=constitution.movement.max_moves)
        if ending is not None:
            return ending, step
        # Their tempo: the wall does NOT cost the step (book ch.3 says it must — see the
        # module docstring; this harness models THEM, it does not endorse the reading).
        cop_view = police_observation(constitution, board=board, position=cop, step=step,
                                      trail=cop_trail)
        cop_truth = referee_belief(constitution, start=thief, smell_trust=SMELL_TRUST)
        walled = cop_brain._decide(cop_view, cop_truth).barrier
        if walled is not None:
            board = board.with_barrier(walled)
            belief.note_barrier(walled)
            cop_view = police_observation(constitution, board=board, position=cop, step=step,
                                          trail=cop_trail)
        cop = board.apply_move(cop, cop_brain._pick_move(cop_view, cop_truth))
        cop_trail.advance(cop, intensity)
        belief = feed.observe(belief, trail=cop_trail, truth=cop, board=board)
        ending = check_end(board, cop_pos=cop, thief_pos=thief, steps_survived=step,
                           survival_threshold=threshold, max_moves=constitution.movement.max_moves)
        if ending is not None:
            return ending, step
    return Outcome.THIEF_SURVIVAL, threshold


def test_the_pre_m7_46_thief_loses_the_signed_start(constitution: Constitution) -> None:
    """Reproduces the friendly: g02/g04/g06 all ended cop_capture from this start."""
    options = {**deployed_options(), "siege_min_walls": 99.0}  # never fires: quota is 14
    outcome, _steps = play_at_live_tempo(constitution, ThiefBrain(seed=1, options=options))
    assert outcome is Outcome.COP_CAPTURE


def test_the_shipped_thief_survives_the_signed_start(constitution: Constitution) -> None:
    outcome, steps = play_at_live_tempo(constitution, ThiefBrain(seed=1, options=deployed_options()))
    assert outcome is Outcome.THIEF_SURVIVAL
    assert steps == constitution.movement.survival_threshold

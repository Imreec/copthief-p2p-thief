"""Deception timing pins (TODO M5-3; PRD_thief_brain §3) — ⚑ thief repo only.

The M3-4 lie mechanism gets its policy: the self-mirror (a second BeliefFilter over
OUR OWN emitted evidence, public API only) estimates what a rational opponent can
know; the brain lies exactly in the sharp-mirror × near-cop quadrant, decoys away
from its actual heading, respects budget and cooldown, and seals intent truthfully
through the hint-intent seam.
"""

from pathlib import Path

from copthief_core.domain.belief import BeliefFilter
from copthief_core.shared.config import load_all, load_gazetteer
from copthief_core.strategy.brains import Observation
from copthief_core.strategy.hints import VERDICT_LIE
from copthief_thief.brain import ThiefBrain
from copthief_thief.deception import SelfMirror

CONSTITUTION, PRIVATE, _LIMITS = load_all(Path("config"), counted=False)
GAZETTEER = load_gazetteer(
    Path("config") / "gazetteer.json",
    map_area=CONSTITUTION.world.map_area,
    board=CONSTITUTION.board.make_board(),
)
MOVE_SET = CONSTITUTION.movement.move_set


def _observation(
    position: tuple[int, int], *, step: int, own_smell: dict[str, float]
) -> Observation:
    return Observation(
        board=CONSTITUTION.board.make_board(),
        position=position,
        move_set=MOVE_SET,
        role="thief",
        step=step,
        gazetteer=GAZETTEER,
        own_smell=own_smell,
        pheromones=CONSTITUTION.pheromones,
    )


def _belief(cop_at: tuple[int, int]) -> BeliefFilter:
    return BeliefFilter(
        board=CONSTITUTION.board.make_board(),
        move_set=MOVE_SET,
        start=cop_at,
        center_intensity=CONSTITUTION.pheromones.center_intensity,
        decay=CONSTITUTION.pheromones.decay,
        smell_trust=PRIVATE.smell_trust_weight,
        hint_trust=PRIVATE.hint_trust_default,
    )


def _fresh_grid(cell: tuple[int, int]) -> dict[str, float]:
    """A transmitted grid whose fresh center sits exactly on `cell` (sharp evidence)."""
    value = round(
        CONSTITUTION.pheromones.center_intensity - CONSTITUTION.pheromones.decay, 3
    )
    return {f"{cell[0]},{cell[1]}": value}


def test_self_mirror_sharpens_on_our_true_cell_under_our_honest_trail() -> None:
    mirror = SelfMirror(
        board=CONSTITUTION.board.make_board(),
        move_set=MOVE_SET,
        start=CONSTITUTION.board.thief_start,
        pheromones=CONSTITUTION.pheromones,
        smell_trust=PRIVATE.smell_trust_weight,
    )
    here = CONSTITUTION.board.thief_start
    mirror.observe_turn(_fresh_grid(here))
    assert mirror.exposure(here) > 0.5  # our own fresh center gives us away


def test_lies_exactly_in_the_sharp_mirror_near_cop_quadrant() -> None:
    brain = ThiefBrain(seed=5)
    position = (3, 3)
    # Far cop + no transmitted evidence: no reason to burn a lie.
    quiet = brain.decide(_observation(position, step=1, own_smell={}), _belief((0, 6)))
    assert quiet.hint_verdict is None
    # Near cop + our own fresh center transmitted: they know and can act - lie.
    exposed = brain.decide(
        _observation(position, step=2, own_smell=_fresh_grid(position)), _belief((3, 1))
    )
    assert exposed.hint_verdict == VERDICT_LIE
    assert exposed.hint_landmark in GAZETTEER.landmarks()


def test_the_decoy_points_away_from_the_actual_heading() -> None:
    brain = ThiefBrain(seed=5)
    position = (3, 3)
    decision = brain.decide(
        _observation(position, step=2, own_smell=_fresh_grid(position)), _belief((3, 1))
    )
    assert decision.hint_verdict == VERDICT_LIE
    board = CONSTITUTION.board.make_board()
    dest = board.apply_move(position, decision.move)
    truthful = GAZETTEER.nearest(dest)
    assert decision.hint_landmark != truthful  # the lie never names where we are going


def test_lie_budget_and_cooldown_are_respected() -> None:
    brain = ThiefBrain(seed=5, options={"lie_budget": 1.0, "lie_cooldown": 3.0})
    position = (3, 3)
    lies = 0
    for step in range(1, 8):
        decision = brain.decide(
            _observation(position, step=step, own_smell=_fresh_grid(position)),
            _belief((3, 1)),
        )
        lies += decision.hint_verdict == VERDICT_LIE
    assert lies == 1  # the budget caps the whole mini-game

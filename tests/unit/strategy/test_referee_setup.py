"""Referee fixtures under a selected scent model (M7-14).

The arena/GA path had no scent-model door at all — every referee game ran the
reference physics regardless of `[scent] model`, so GA weights were tuned under a
model the counted series will not play. These pin the new door: a passed model reaches
BOTH the trail (emission physics) and the belief (observation model), and omission
stays byte-identical to the legacy construction.
"""

from pathlib import Path

from copthief_core.domain.scent_book import MultiplicativeBookV1
from copthief_core.shared.config import load_all
from copthief_core.shared.locked_models import build_scent_model
from copthief_core.strategy.referee_setup import referee_belief, referee_trail

CONSTITUTION, PRIVATE, _ = load_all(Path("config"), counted=False)
BOOK = build_scent_model(PRIVATE.locked_models, "multiplicative_book_v1", CONSTITUTION.pheromones)


def test_a_passed_model_reaches_the_trail_physics() -> None:
    trail = referee_trail(CONSTITUTION, model=BOOK)
    assert isinstance(trail.model, MultiplicativeBookV1)


def test_a_passed_model_reaches_the_belief_observation_model() -> None:
    belief = referee_belief(CONSTITUTION, start=(3, 3), smell_trust=1.0, scent_model=BOOK)
    # The filter has no public model accessor by design (PRD_belief §7); the wiring
    # pin reads the private slot rather than adding surface for a test.
    assert belief._scent is BOOK  # noqa: SLF001


def test_omission_keeps_the_reference_construction() -> None:
    trail = referee_trail(CONSTITUTION)
    assert not isinstance(trail.model, MultiplicativeBookV1)
    assert trail.model.name == "subtractive_chebyshev_v1"

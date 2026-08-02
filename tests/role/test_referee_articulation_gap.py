"""The instrument↔wire gap on `w_articulation` (M7-30 probe finding) — ⚑ thief repo.

`ThiefBrain` prices its articulation trap-awareness only "while the cop's quota can still
pay for it" — `observation.barriers_used < observation.max_barriers`. The live peer path
fills both fields (`peer/turns.py`: the session's own placements, which is 0 for a thief,
against the signed quota), so the branch is ALWAYS live on the wire. Referee mode fills
NEITHER (`strategy/referee_obs.thief_observation`), so `0 < 0` is false and the branch is
NEVER live in the instrument.

Consequence, and the reason these pins exist: the arena cannot see `w_articulation` at
all, so the M7-16 and M7-21 runs evolved it as free drift and every committed thief arena
table describes a thief we do not field. M7-30 answers it the only way a thief-repo change
can — by deploying the one value at which instrument and wire provably agree, `0.0` — and
names the core fix (referee_obs carrying the quota, police-lead) as the follow-up.

These are REGRESSION pins on a known gap, not approval of it: when the core fix lands,
`test_referee_mode_cannot_see_the_gene` is expected to go red and should be deleted with
the same commit that makes the instrument honest.
"""

from pathlib import Path

from copthief_core.domain.rules import Outcome
from copthief_core.shared.config import load_all
from copthief_core.shared.locked_models import build_scent_model
from copthief_core.strategy.brains import make_brain
from copthief_core.strategy.referee import play_referee_game
from copthief_core.strategy.referee_obs import police_observation, thief_observation
from copthief_core.strategy.referee_setup import referee_trail
from copthief_core.strategy.scenarios import scenario_suite

CONFIG_DIR = Path("config")

DEPLOYED = {
    "ramp_multiplier": 3.546170631626467,
    "ramp_start_fraction": 0.3,
    "trap_size_fraction": 0.20126612510301556,
    "w_distance": 4.562212626629817,
    "w_region": 2.030098462268734,
    "w_spread": 1.7843591354096908,
}


def test_referee_thief_observation_carries_no_quota_but_the_police_one_does() -> None:
    constitution, _, _ = load_all(CONFIG_DIR, counted=False)
    board = constitution.board.make_board()
    trail = referee_trail(constitution)
    thief_view = thief_observation(
        constitution, board=board, position=(3, 3), step=1, trail=trail, gazetteer=None
    )
    police_view = police_observation(
        constitution, board=board, position=(0, 0), step=1, trail=trail
    )
    # The root cause, asserted directly rather than inferred from a game outcome.
    assert (thief_view.barriers_used, thief_view.max_barriers) == (0, 0)
    assert police_view.max_barriers == constitution.movement.max_barriers


def test_referee_mode_cannot_see_the_gene() -> None:
    """Three decades apart on `w_articulation`, identical games — the gene is inert."""
    constitution, private, _ = load_all(CONFIG_DIR, counted=False)
    model = build_scent_model(
        private.locked_models, "multiplicative_book_v1", constitution.pheromones
    )
    scenarios = scenario_suite(constitution, seeds=range(601, 609), min_separation=4)
    outcomes: list[list[tuple[Outcome, int]]] = []
    for weight in (0.0, 8.928429525952911, 40.0):
        played = [
            play_referee_game(
                constitution,
                police_brain=make_brain(
                    "ref-police", seed=2 * s.seed, options={"ref_police_barrier_chance": 0.15}
                ),
                thief_brain=make_brain(
                    "copthief_thief.brain:ThiefBrain",
                    seed=2 * s.seed + 1,
                    options={**DEPLOYED, "w_articulation": weight},
                ),
                smell_trust=private.smell_trust_weight,
                seed=s.seed,
                cop_start=s.cop_start,
                thief_start=s.thief_start,
                scent_model=model,
            )
            for s in scenarios
        ]
        outcomes.append([(r.outcome, r.steps) for r in played])
    assert outcomes[0] == outcomes[1] == outcomes[2]

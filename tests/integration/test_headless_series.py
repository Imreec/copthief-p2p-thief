"""M3-5 DoD: full headless series with the baseline brains, referee AND peer modes.

Referee mode: the strategy/referee harness holds ground truth and resolves endings
with the one rules module (all three capture forms live). Peer mode: the same brains
drive full protocol games over the queue transports with sealing + mutual audit —
one rules module, two modes (PLAN §3).
"""

from pathlib import Path

from copthief_core.domain.rules import Outcome
from copthief_core.peer.match import run_local_minigame
from copthief_core.shared.config import load_all
from copthief_core.strategy.referee import play_referee_series

CONSTITUTION, PRIVATE, _LIMITS = load_all(Path("config"), counted=False)
SEEDS = (1, 2, 3, 4, 5)


def test_referee_series_runs_headless_and_ends_every_game_legally() -> None:
    results = play_referee_series(
        CONSTITUTION,
        police_brain_name="greedy-manhattan",
        thief_brain_name="random",
        smell_trust=PRIVATE.smell_trust_weight,
        seeds=SEEDS,
    )
    assert len(results) == len(SEEDS)
    for result in results:
        assert result.outcome in (Outcome.COP_CAPTURE, Outcome.THIEF_SURVIVAL)
        assert 1 <= result.steps <= CONSTITUTION.movement.survival_threshold
        if result.outcome is Outcome.THIEF_SURVIVAL:
            assert result.steps == CONSTITUTION.movement.survival_threshold


def test_referee_series_is_seed_reproducible() -> None:
    kwargs = {
        "police_brain_name": "random",
        "thief_brain_name": "greedy-manhattan",
        "smell_trust": PRIVATE.smell_trust_weight,
        "seeds": SEEDS,
    }
    assert play_referee_series(CONSTITUTION, **kwargs) == play_referee_series(
        CONSTITUTION, **kwargs
    )


def test_referee_mode_greedy_police_catches_a_random_thief_sometimes() -> None:
    # Not a strength claim — only that the capture path is reachable headless: across
    # this fixed seed set the greedy chaser must land at least one capture.
    results = play_referee_series(
        CONSTITUTION,
        police_brain_name="greedy-manhattan",
        thief_brain_name="random",
        smell_trust=PRIVATE.smell_trust_weight,
        seeds=range(1, 21),
    )
    assert any(r.outcome is Outcome.COP_CAPTURE for r in results)


def test_peer_mode_series_with_config_brains_audits_clean_every_game() -> None:
    for seed in (1, 2, 3):
        result = run_local_minigame(Path("config"), police_seed=seed, thief_seed=seed + 100)
        assert result.outcome in ("thief_survival", "cop_capture")
        assert result.audit_ok_police_side
        assert result.audit_ok_thief_side


def test_private_settings_carry_resolvable_strategy_classes() -> None:
    # Role-blind (PR #29 rule): each repo's game.toml may name its own role package
    # via the book s6.2 dotted notation - the pin is that the factory resolves it.
    from copthief_core.strategy.brains import BrainBase, make_brain

    assert isinstance(make_brain(PRIVATE.police_class, seed=1), BrainBase)
    assert isinstance(make_brain(PRIVATE.thief_class, seed=1), BrainBase)

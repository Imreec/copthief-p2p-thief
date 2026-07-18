"""PLAN §13 M1 exit evidence (in-process half): full mini-game, sealing, self-audit pass.

Two symmetric peer loops play a complete mini-game through the in-process queue
transports — the reference's push/inbox convention (M2 F1) with zero network — ending in
survival, with both directions' audits re-hashed clean. The two-process localhost form of
the same run lives in tests/integration/test_p2p_live.py (excluded from keyless CI).

The probed seed outcomes below hold for the M1 RANDOM walk, so both brain classes are
pinned to it through a tmp config tree — role-agnostic (PR #29 rule): each repo ships
its own `[strategy]` classes and these M1 pins must not depend on them.
"""

import re
import shutil
from pathlib import Path

import pytest

from copthief_core.domain.state_machine import GameState
from copthief_core.peer.match import run_local_minigame

CONFIG_DIR = Path("config")


@pytest.fixture(scope="module")
def m1_config(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The shipped config tree with BOTH brain classes pinned to the M1 random walk."""
    config = tmp_path_factory.mktemp("m1") / "config"
    shutil.copytree(CONFIG_DIR, config)
    toml_path = config / "game.toml"
    text, hits = re.subn(
        r'(police_class|thief_class) = "[^"]*"',
        r'\1 = "random"',
        toml_path.read_text(encoding="utf-8"),
    )
    assert hits == 2, "game.toml lost a strategy class key"
    toml_path.write_text(text, encoding="utf-8")
    return config


def test_full_minigame_over_queue_transports_self_audits_clean(m1_config: Path) -> None:
    result = run_local_minigame(m1_config, police_seed=1, thief_seed=2)  # probed: survival
    assert result.outcome == "thief_survival"
    assert result.audit_ok_police_side
    assert result.audit_ok_thief_side
    assert result.steps == result.survival_threshold  # the thief's survival turn count
    assert result.game_uid  # both peers derived the same shared id
    assert result.police_state is GameState.GAME_OVER
    assert result.thief_state is GameState.GAME_OVER
    assert result.scores == (result.survival_cop_points, result.survival_thief_points)


def test_capture_ends_the_game_early_with_the_capture_scores(m1_config: Path) -> None:
    # SQ2 flow end-to-end: seeds (3, 3) collide at step 4 (probed) — the police's
    # landing-cell claim is answered caught=true, both sides audit clean, capture row pays.
    result = run_local_minigame(m1_config, police_seed=3, thief_seed=3)
    assert result.outcome == "cop_capture"
    assert result.steps < result.survival_threshold
    assert result.audit_ok_police_side
    assert result.audit_ok_thief_side
    assert result.police_state is GameState.GAME_OVER
    assert result.thief_state is GameState.GAME_OVER
    from copthief_core.shared.config import load_all

    scoring = load_all(CONFIG_DIR, counted=False)[0].scoring
    assert result.scores == (scoring.capture_cop, scoring.capture_thief)


def test_minigame_is_reproducible_for_fixed_seeds() -> None:
    a = run_local_minigame(CONFIG_DIR, police_seed=7, thief_seed=13)
    b = run_local_minigame(CONFIG_DIR, police_seed=7, thief_seed=13)
    assert a.police_moves == b.police_moves
    assert a.thief_moves == b.thief_moves

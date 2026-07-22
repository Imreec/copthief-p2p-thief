"""The derived sparring config is safe by construction (M7-1).

Role-agnostic on purpose (gotcha #9): this test runs unchanged in both repos, so it may
never name a role's option table — it asserts that whatever tuned table THIS repo ships
is gone from the derived config, and that the derived config passes the guard.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from copthief_core.shared.config import load_all
from copthief_core.shared.sparring import (
    SparringUnsafeError,
    assert_sparring_safe,
    sparring_problems,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from make_sparring_config import (  # noqa: E402
    TUNING_ARTIFACTS,
    derive,
    rest_email,
    strip_tuned_tables,
)

SOURCE = Path("config")


def test_this_repo_ships_a_tuned_table_so_the_test_below_is_not_vacuous() -> None:
    _, shipped, _ = load_all(SOURCE, counted=False)
    assert sparring_problems(shipped), "no tuned weights shipped: the derivation proves nothing"


def test_the_derived_config_passes_the_guard(tmp_path: Path) -> None:
    out = derive(SOURCE, tmp_path / "config-sparring")
    _, private, _ = load_all(out, counted=False)
    assert_sparring_safe(private)  # no raise
    assert not private.police_options
    assert not private.thief_options
    assert not private.email.enabled
    assert private.email.recipient == ()


def test_the_signed_constitution_is_copied_byte_for_byte(tmp_path: Path) -> None:
    """The terms signature and `config_sha256` are computed over these bytes — a
    sparring host that negotiates different terms is not our peer at all."""
    out = derive(SOURCE, tmp_path / "config-sparring")
    assert (out / "game.json").read_bytes() == (SOURCE / "game.json").read_bytes()


def test_the_brain_selection_itself_survives(tmp_path: Path) -> None:
    """Only the WEIGHTS are dropped, not the class: a sparring target that runs a
    different brain exercises a code path our real peer never plays."""
    out = derive(SOURCE, tmp_path / "config-sparring")
    _, shipped, _ = load_all(SOURCE, counted=False)
    _, private, _ = load_all(out, counted=False)
    assert private.police_class == shipped.police_class
    assert private.thief_class == shipped.thief_class


def test_a_source_that_cannot_be_made_safe_is_refused(tmp_path: Path) -> None:
    """The derivation is not a rubber stamp — and this is a REAL gap, not a contrived one.

    `strip_tuned_tables` removes `[strategy.<role>]` section headers, but TOML also
    expresses the same table INLINE under `[strategy]`, which the loader reads
    identically. The text transform cannot see it; the guard can, because it inspects the
    LOADED settings. That is exactly why the derivation validates its own output instead
    of trusting its own edits. (Naming a role here is safe under gotcha #9: the loader
    reads both role keys in both repos, so nothing couples to this repo's config.)
    """
    source = tmp_path / "hostile"
    source.mkdir()
    for candidate in SOURCE.iterdir():
        if candidate.is_file() and candidate.name != "game.toml":
            (source / candidate.name).write_bytes(candidate.read_bytes())
    text = (SOURCE / "game.toml").read_text(encoding="utf-8")
    hostile = text.replace("[strategy]\n", "[strategy]\npolice = { w_distance = 3.8875 }\n", 1)
    (source / "game.toml").write_text(hostile, encoding="utf-8")
    with pytest.raises(SparringUnsafeError, match="tuned"):
        derive(source, tmp_path / "out")


def test_tuning_artifacts_never_reach_the_derived_config(tmp_path: Path) -> None:
    """GA weights and arena rosters carry the numbers that may not deploy to a standing
    host. The peer does not read them — but a config directory holding them is one
    `--config` away from being played, so they are left behind, not merely ignored."""
    out = derive(SOURCE, tmp_path / "config-sparring")
    landed = {p.name for p in out.iterdir()}
    assert not (landed & TUNING_ARTIFACTS)
    present_in_source = {p.name for p in SOURCE.iterdir()} & TUNING_ARTIFACTS
    assert present_in_source, "no tuning artifacts shipped: this assertion proves nothing"


def test_the_transforms_are_idempotent() -> None:
    text = (SOURCE / "game.toml").read_text(encoding="utf-8")
    once = rest_email(strip_tuned_tables(text))
    assert rest_email(strip_tuned_tables(once)) == once


def test_the_cli_refuses_a_sparring_run_on_the_shipped_config(
    capsys: pytest.CaptureFixture,
) -> None:
    """The rule at the moment of use: `--sparring` against what we actually play with is
    a clean JSON refusal and exit 2 — readable in an ops window, not a traceback."""
    from copthief_core.sdk.cli import main

    code = main(["run", "peer", "--role", "police", "--sparring"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["refused"] == "sparring-unsafe config"
    assert any("tuned" in problem for problem in payload["problems"])

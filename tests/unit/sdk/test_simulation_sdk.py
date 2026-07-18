"""SimulationSdk facade (PLAN §3; PRD FR-14): the single business entry point."""

from pathlib import Path

from copthief_core.sdk.simulation import SimulationSdk


def test_run_local_match_flows_through_the_facade() -> None:
    sdk = SimulationSdk(Path("config"))
    result = sdk.run_local_match(police_seed=1, thief_seed=2)
    # Outcome-agnostic (PR #29 rule): the shipped [strategy] classes differ per
    # repo and per tuning drop - the facade flow + clean audits are the pin.
    assert result.outcome in ("thief_survival", "cop_capture")
    assert result.audit_ok_police_side
    assert result.audit_ok_thief_side


def test_facade_exposes_the_loaded_constitution() -> None:
    sdk = SimulationSdk(Path("config"))
    assert sdk.constitution.board.grid_size >= 7
    assert sdk.private.my_port > 0

"""M7-7(1): the three timing budgets are reconciled EXPLICITLY, at config load.

The kill drill's real lesson is that two budgets were set independently and their
ordering was never stated anywhere: the signed `watchdog_timeout_sec` (60) and the
private `turn_timeout_seconds` (180) only met at runtime, and the wrong one won. The
relationship is now a loader assertion, so a config that would self-terminate us
refuses to load instead of losing a counted game.

`watchdog_timeout_sec` is a SIGNED value (App F `network_and_league`): every case here
moves PRIVATE budgets only — the fix is semantics, never a config bump.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from config_fixtures import CONFIG_DIR, copy_config, set_toml_number

from copthief_core.shared.budgets import io_stall_timeout, reconcile_budgets
from copthief_core.shared.config import ConfigError, load_all


def test_the_shipped_config_is_reconciled() -> None:
    constitution, private, _limits = load_all(CONFIG_DIR, counted=False)
    reconcile_budgets(constitution, private)  # the shipped tree is the reference case


def test_the_io_budget_sits_strictly_behind_our_own_turn_deadline() -> None:
    """The blocker in one assertion: whatever a stalled transport does, our own rule
    budget is the one that expires first, so silence is classified, not self-inflicted."""
    constitution, private, _limits = load_all(CONFIG_DIR, counted=False)
    assert io_stall_timeout(constitution, private) > private.turn_timeout_seconds
    assert constitution.league.watchdog_timeout_sec <= private.turn_timeout_seconds


def test_an_outbound_give_up_may_not_outlast_the_turn_budget(tmp_path: Path) -> None:
    """connect_timeout > turn_timeout would mean the transport abandons a peer our own
    deadline still considers in-budget."""
    clone = copy_config(tmp_path)
    set_toml_number(clone, "turn_timeout_seconds", 30)
    with pytest.raises(ConfigError) as error:
        load_all(clone, counted=False)
    assert "connect_timeout_seconds" in str(error.value)


def test_a_poll_interval_over_the_loop_budget_is_refused(tmp_path: Path) -> None:
    """An idle loop beats once per poll: if a poll can outlast the loop budget, a
    perfectly healthy waiting peer self-terminates."""
    clone = copy_config(tmp_path)
    set_toml_number(clone, "poll_interval_seconds", 90.0)
    with pytest.raises(ConfigError) as error:
        load_all(clone, counted=False)
    assert "poll_interval_seconds" in str(error.value)


def test_every_violation_is_listed_at_once() -> None:
    """The App F guard's habit: refuse loudly with the whole list, never one at a time."""
    constitution, private, _limits = load_all(CONFIG_DIR, counted=False)
    broken = replace(private, poll_interval_seconds=999.0, connect_timeout_seconds=9999.0)
    with pytest.raises(ConfigError) as error:
        reconcile_budgets(constitution, broken)
    assert "poll_interval_seconds" in str(error.value)
    assert "connect_timeout_seconds" in str(error.value)


def test_a_zero_watchdog_budget_is_refused() -> None:
    constitution, private, _limits = load_all(CONFIG_DIR, counted=False)
    league = replace(constitution.league, watchdog_timeout_sec=0)
    with pytest.raises(ConfigError):
        reconcile_budgets(replace(constitution, league=league), private)


def test_a_call_deadline_at_or_over_the_signed_response_budget_is_refused() -> None:
    """M7-57 rule 6: ONE outbound call must end inside the deadline the opponent enforces.

    The live defect had no clock at all here — the call inherited the transport library's
    default, so a delivered-but-unanswered push blocked far past the signed budget and the
    retry landed 61 s late. Equality is refused too: a call that exactly fills the deadline
    leaves no room for the retry that is the whole point of having one.
    """
    constitution, private, _limits = load_all(CONFIG_DIR, counted=False)
    signed = constitution.league.response_timeout_sec
    with pytest.raises(ConfigError) as error:
        reconcile_budgets(constitution, replace(private, call_timeout_seconds=float(signed)))
    assert "call_timeout_seconds" in str(error.value)
    assert "response_timeout_sec" in str(error.value)


def test_the_shipped_call_deadline_leaves_room_for_a_retry() -> None:
    """The value we actually ship must fit a first attempt AND a retry inside the budget."""
    constitution, private, _limits = load_all(CONFIG_DIR, counted=False)
    reconcile_budgets(constitution, private)  # the shipped pair reconciles
    assert private.call_timeout_seconds * 2 < constitution.league.response_timeout_sec

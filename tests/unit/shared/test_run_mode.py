"""RunMode (M7-9): rules enforcement and lecturer reachability are separate axes.

One flag used to do both jobs. Arming the App F fixed rows (a real six-mini-game
series, no deviations) was the SAME switch that made the lecturer addressable, so a
dress rehearsal could not have the first without the second: play by the real rules,
or keep the lecturer unreachable — never both.

Imree's framing (2026-07-24): a friendly should differ from a counted game ONLY in
that it is not counted and the lecturer is not on it — full ninety minutes, same rules.
That needs two switches. The invariant below is what keeps the split from weakening the
guard it replaces: the lecturer needs BOTH, so unlocking him never gets easier than it
is today (Alon/Renat: "safety by shape, not by configuration").
"""

from __future__ import annotations

import pytest

from copthief_core.shared.run_mode import RunMode


def test_the_default_is_the_safe_one() -> None:
    mode = RunMode()
    assert mode.strict_rules is False
    assert mode.counted_series is False
    assert mode.lecturer_addressable is False


def test_a_rehearsal_arms_the_rules_but_never_the_lecturer() -> None:
    """The mode this whole split exists for: the full rulebook, and a lecturer who is
    structurally unreachable rather than merely unconfigured."""
    mode = RunMode.rehearsal()
    assert mode.strict_rules is True
    assert mode.counted_series is False
    assert mode.lecturer_addressable is False


def test_a_counted_series_arms_both() -> None:
    mode = RunMode.counted()
    assert mode.strict_rules is True
    assert mode.counted_series is True
    assert mode.lecturer_addressable is True


def test_the_lecturer_can_never_be_reached_without_the_rules_armed() -> None:
    """The invariant that keeps the split from weakening the guard: a counted series
    without strict rules cannot be constructed at all, so no combination of flags
    reaches the lecturer from a config the App F rows never vetted."""
    with pytest.raises(ValueError, match="strict"):
        RunMode(strict_rules=False, counted_series=True)


def test_lecturer_reachability_is_exactly_the_counted_axis() -> None:
    """Pinned as an identity rather than a coincidence: nothing else may unlock him."""
    for strict in (True, False):
        for counted in (True, False):
            if counted and not strict:
                continue  # refused by the invariant above
            mode = RunMode(strict_rules=strict, counted_series=counted)
            assert mode.lecturer_addressable is counted


def test_the_dev_default_still_refuses_app_f_enforcement() -> None:
    """Everyday development is not a rehearsal: the fixed rows stay disarmed so a
    one-off game can run on a config that is not a six-mini-game constitution."""
    assert RunMode().strict_rules is False

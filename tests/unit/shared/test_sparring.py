"""Sparring-host safety guard (M7-1): the rule made mechanical, not remembered.

CLAUDE.md §9/§10: a standing host runs the GENERIC brain only — tuned weights never
deploy there — and ADR-0008 decision 6 pins it to a non-sending posture. Both are
properties of a loaded config, so both are checkable, and this is the check.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from copthief_core.shared.config import load_all
from copthief_core.shared.sparring import SparringUnsafeError, assert_sparring_safe

_CONSTITUTION, SHIPPED, _LIMITS = load_all(Path("config"), counted=False)


def _safe() -> object:
    """The shipped private settings, reduced to a sparring-safe posture."""
    return replace(
        SHIPPED,
        police_options={},
        thief_options={},
        email=replace(SHIPPED.email, enabled=False, recipient=()),
    )


def test_a_sparring_safe_config_passes() -> None:
    assert_sparring_safe(_safe())  # no raise


def test_tuned_weights_are_refused_whichever_role_carries_them() -> None:
    """Role-agnostic on purpose (gotcha #9): the cop repo ships `[strategy.police]`
    weights and the thief repo ships `[strategy.thief]` ones — the guard must refuse
    either, so this test names neither."""
    for field in ("police_options", "thief_options"):
        tuned = replace(_safe(), **{field: {"w_distance": 3.8875}})
        with pytest.raises(SparringUnsafeError, match="tuned"):
            assert_sparring_safe(tuned)


def test_a_sending_email_posture_is_refused() -> None:
    settings = _safe()
    armed = replace(settings, email=replace(settings.email, enabled=True))
    with pytest.raises(SparringUnsafeError, match="email"):
        assert_sparring_safe(armed)


def test_a_configured_recipient_is_refused_even_while_disabled() -> None:
    """The authorization IS the recipient (ADR-0008): a host that carries an address is
    one flag away from sending, so the address itself is what may not be there."""
    settings = _safe()
    addressed = replace(
        settings, email=replace(settings.email, recipient=("someone@example.test",))
    )
    with pytest.raises(SparringUnsafeError, match="recipient"):
        assert_sparring_safe(addressed)


def test_every_violation_is_reported_at_once() -> None:
    """The App F guard's habit: a config is fixed in one pass or not at all."""
    settings = _safe()
    broken = replace(
        settings,
        police_options={"w_distance": 3.8875},
        email=replace(settings.email, enabled=True, recipient=("someone@example.test",)),
    )
    with pytest.raises(SparringUnsafeError) as error:
        assert_sparring_safe(broken)
    message = str(error.value)
    assert "tuned" in message
    assert "email" in message
    assert "recipient" in message


def test_the_shipped_config_is_not_sparring_safe() -> None:
    """The guard would be worthless if it passed what we actually play with: this repo
    ships tuned weights for its own role, and that is exactly what must never deploy."""
    with pytest.raises(SparringUnsafeError):
        assert_sparring_safe(SHIPPED)

"""M7-6b lecturer guard: the lecturer is addressable ONLY from a counted run.

Imree's standing rule — "no email is ever sent to the lecturer without my explicit word" —
was policy in a document until now: the interlock refused a run with NO recipient, but it
had no idea which address belonged to the lecturer, so a friendly that named him would
have mailed him automatically.

The mechanism reuses a switch that already exists and already has teeth: `counted`. The
App F guard arms the counted-series rows only when it is set, so a counted run REFUSES TO
LOAD unless `num_games` is exactly 6 and every fixed value matches (PRD_engine §6.1) —
you cannot be in counted mode by accident. Tying the lecturer to that flag means the
deliberate act is the one already required to play a real game, with no extra ceremony
added to friendlies.
"""

from __future__ import annotations

import pytest

from copthief_core.report.email_interlock import decide_email_action

LECTURER = "rmisegal+uoh26finalgame@gmail.com"
US = "imreeyal.copthief@gmail.com"
PEER = "peer.team@example.test"


def decide(recipients: tuple[str, ...], *, lecturer_addressable: bool) -> str:
    return decide_email_action(
        enabled=True,
        mode="send",
        recipients=recipients,
        lecturer_addressable=lecturer_addressable,
        lecturer=LECTURER,
    ).action


def test_a_friendly_may_never_address_the_lecturer() -> None:
    """The whole point: policy becomes mechanism."""
    assert decide((LECTURER,), lecturer_addressable=False) == "refuse"


def test_the_lecturer_cannot_ride_along_beside_a_friendly_recipient() -> None:
    """Hiding him in a list must not work either — the book calls his address the SOLE
    binding one, so a counted report never CCs a peer and a friendly never includes him."""
    assert decide((US, PEER, LECTURER), lecturer_addressable=False) == "refuse"


def test_a_counted_run_addresses_the_lecturer_normally() -> None:
    """lecturer_addressable=True cannot be reached by accident: the App F guard refuses to load a
    constitution that is not a genuine counted series."""
    assert decide((LECTURER,), lecturer_addressable=True) == "send"


def test_friendlies_are_untouched_by_the_guard() -> None:
    """No new ceremony for the common case — us + the opponent team, automatic."""
    assert decide((US, PEER), lecturer_addressable=False) == "send"
    assert decide((US,), lecturer_addressable=False) == "send"


@pytest.mark.parametrize(
    "written",
    [
        LECTURER.upper(),
        f"  {LECTURER}  ",
        LECTURER.replace("rmisegal", "RMisegal"),
    ],
)
def test_the_guard_is_not_fooled_by_case_or_whitespace(written: str) -> None:
    """An address that reaches the same mailbox must be caught however it was typed."""
    assert decide((written,), lecturer_addressable=False) == "refuse"


def test_the_refusal_names_the_lecturer_gate() -> None:
    decision = decide_email_action(
        enabled=True,
        mode="send",
        recipients=(LECTURER,),
        lecturer_addressable=False,
        lecturer=LECTURER,
    )
    assert "lecturer" in decision.reason
    assert "counted" in decision.reason


def test_an_unconfigured_lecturer_address_disables_the_guard_not_the_rail() -> None:
    """With no lecturer configured there is nobody to protect; ordinary sending stands."""
    assert (
        decide_email_action(
            enabled=True, mode="send", recipients=(US,), lecturer_addressable=False, lecturer=""
        ).action
        == "send"
    )

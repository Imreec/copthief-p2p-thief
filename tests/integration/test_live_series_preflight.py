"""A report-owing series refuses to START if it cannot deliver its report (M7-10b).

Imree's demand, made mechanical: a rehearsal is a counted game minus the counting, so
the auto-fired report is part of the format. What must be decided is decided BEFORE the
series — an empty recipient, a disabled rail, or a rehearsal pointed at the lecturer is
caught before a single sub-game is played, never after all six settle (App E rule 35
makes the late discovery the costliest). A dev run owes no report and is exempt.
"""

from __future__ import annotations

from pathlib import Path

from live_series_harness import CONFIG, rehearsal_sdk, run
from series_fixtures import SERIES_LENGTH

from copthief_core.sdk.simulation import SimulationSdk
from copthief_core.shared.run_mode import RunMode


def test_a_rehearsal_addressed_only_to_the_lecturer_refuses_before_it_plays(
    tmp_path: Path,
) -> None:
    """M7-9 + M7-10b: a rehearsal cannot reach the lecturer, and the catch now sits at
    the TOP of the run — a rehearsal whose only recipient is unreachable never plays a
    single sub-game, rather than playing six and then failing to report."""
    lecturer = "lecturer@example.test"
    outcome, mail, seen = run(rehearsal_sdk(recipient=(lecturer,), lecturer=lecturer), tmp_path)

    assert "refused" in outcome
    assert "counted" in outcome["problems"][0]  # the lecturer-not-addressable reason
    assert seen == []  # nothing was played
    assert mail.sends == []


def test_a_rehearsal_with_the_mail_disabled_refuses_before_it_plays(tmp_path: Path) -> None:
    """The core of the demand: a rehearsal MUST fire a report, so a disabled rail is not
    a rehearsal — refused before any game is played rather than discovered after the
    sixth. The committed resting `[email]` is exactly this state."""
    sdk = SimulationSdk(CONFIG, mode=RunMode.rehearsal())
    outcome, mail, seen = run(sdk, tmp_path)

    assert "refused" in outcome
    assert "disabled" in outcome["problems"][0]
    assert seen == []
    assert mail.sends == []


def test_a_dev_series_owes_no_report_and_runs_without_mail(tmp_path: Path) -> None:
    """The exemption: a plain (non-rehearsal, non-counted) run does not owe a report, so
    it is not forced to configure one — the preflight fires only for a run that owes."""
    sdk = SimulationSdk(CONFIG, mode=RunMode())  # dev: rules disarmed
    outcome, _mail, seen = run(sdk, tmp_path)

    assert "refused" not in outcome
    assert len(seen) == SERIES_LENGTH

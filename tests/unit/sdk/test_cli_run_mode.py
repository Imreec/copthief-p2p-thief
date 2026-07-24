"""How a run is governed reaches the CLI (M7-9 residual): `--rehearsal` / `--counted`.

`RunMode` was built and merged, then passed by nothing — so every live game, including
the 2026-07-24 rehearsal, ran with the App F rows DISARMED and a counted-shaped
constitution only because it had been set by hand. Rules were followed, not enforced.
These pins are the wiring that makes the rulebook bite during live play.
"""

from __future__ import annotations

import pytest

from copthief_core.sdk.cli_args import build_parser, run_mode_from_args


def _mode(*argv: str) -> object:
    return run_mode_from_args(build_parser().parse_args(list(argv)))


def test_a_plain_peer_run_is_governed_by_nothing() -> None:
    mode = _mode("run", "peer", "--role", "police")
    assert mode.strict_rules is False
    assert mode.counted_series is False


def test_rehearsal_arms_the_rulebook_and_leaves_the_lecturer_unreachable() -> None:
    mode = _mode("run", "peer", "--role", "police", "--rehearsal")
    assert mode.strict_rules is True
    assert mode.lecturer_addressable is False


def test_counted_arms_the_rulebook_and_makes_the_lecturer_addressable() -> None:
    mode = _mode("series", "--role", "police", "--opponent-group", "x", "--counted")
    assert mode.strict_rules is True
    assert mode.lecturer_addressable is True


def test_the_two_governance_flags_are_mutually_exclusive() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["run", "peer", "--role", "police", "--rehearsal", "--counted"])


def test_a_verb_with_no_governance_axis_still_yields_a_mode() -> None:
    """`replay` has no flags to give — the mapping must not depend on them existing."""
    mode = _mode("replay", "--log", "logs/x.jsonl")
    assert mode.strict_rules is False


def test_the_series_verb_needs_the_opponent_group_it_will_report_against() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["series", "--role", "police"])

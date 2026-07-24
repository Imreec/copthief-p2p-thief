"""The sealed step-0 record must declare the REAL sub-game number (M7-4).

Rules 37-38 make the step-0 declaration a truth duty, and it is sealed into the
step-0 commit at the very first moment of a game — so a wrong sub-game index cannot
be repaired in the report afterwards; the game itself carries the false claim.

`sdk/series_run` always passed the real index, but a standalone `run peer` fell back
to the STATIC `[game] sub_game_number` in the TOML. Under the rolling-window series
protocol (each sub-game its own process) every sub-game therefore declared "1".
Caught live in the 2026-07-24 rehearsal against Alon/Renat's team.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from copthief_core.peer.sealing import live_spec_record
from copthief_core.shared.config import load_all

CONSTITUTION, PRIVATE, _LIMITS = load_all(Path("config"), counted=False)


def test_an_explicit_sub_game_number_is_what_gets_sealed() -> None:
    """The override is the whole point: sub-game 4 must not seal the config's 1."""
    record = live_spec_record(PRIVATE, CONSTITUTION, sub_game_number=4)
    assert record.payload["sub_game_number"] == 4


def test_each_sub_game_of_a_series_seals_its_own_index() -> None:
    declared = [
        live_spec_record(PRIVATE, CONSTITUTION, sub_game_number=n).payload["sub_game_number"]
        for n in range(1, 7)
    ]
    assert declared == [1, 2, 3, 4, 5, 6]


def test_omitting_it_still_falls_back_to_the_configured_value() -> None:
    """The fallback stays for single one-off games — the defect was never the
    fallback itself, it was the live series flow never overriding it."""
    record = live_spec_record(PRIVATE, CONSTITUTION)
    assert record.payload["sub_game_number"] == PRIVATE.sub_game_number


def test_the_declaration_is_sealed_so_the_index_changes_the_commit() -> None:
    """Why this could not be patched after the fact: the index is inside the sealed
    step-0 payload, so two sub-game numbers are two different commitments."""
    one = live_spec_record(PRIVATE, CONSTITUTION, sub_game_number=1)
    two = live_spec_record(PRIVATE, CONSTITUTION, sub_game_number=2)
    assert one.payload["sub_game_number"] != two.payload["sub_game_number"]
    assert one.commit != two.commit


def test_the_game_count_rides_the_same_declaration() -> None:
    """The other half of the truth duty, pinned beside it: a six-game series must
    declare six (the `num_games` find, 2026-07-24)."""
    counted = replace(CONSTITUTION, league=replace(CONSTITUTION.league, num_games=6))
    record = live_spec_record(PRIVATE, counted, sub_game_number=3)
    assert record.payload["num_games_declared"] == 6
    assert record.payload["sub_game_number"] == 3


def test_the_cli_exposes_the_sub_game_flag_and_defaults_to_none() -> None:
    """The defect was a missing seam, so the seam itself is pinned: `run peer` must
    accept the real index, and must NOT invent one when omitted."""
    from copthief_core.sdk.cli import _parser

    parsed = _parser().parse_args(["run", "peer", "--role", "thief", "--sub-game", "4"])
    assert parsed.sub_game == 4

    default = _parser().parse_args(["run", "peer", "--role", "thief"])
    assert default.sub_game is None

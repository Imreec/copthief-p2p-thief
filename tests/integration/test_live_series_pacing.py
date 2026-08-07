"""The driver's index pacing end to end (M7-43) — the uoh-sqak drift, reproduced.

`test_series_pacing` pins the decision; these pin that the DRIVER obeys it: a window
that never became a game must not consume a sub-game or leave a row in the record, and a
peer that is strictly ahead must be followed rather than deadlocked against.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from live_series_harness import OPPONENT, rehearsal_sdk
from series_fixtures import RecordingMail, sub_game_log

from copthief_core.sdk.live_series import run_live_series
from copthief_core.sdk.series_pacing import HANDSHAKE_FAILED


def _drive(tmp_path: Path, script: dict[int, list[dict[str, Any]]]) -> list[int]:
    """Run the series with a scripted player; returns the sub-game indices attempted.

    `script` maps a sub-game index to the results its successive attempts return; an
    index with no entry left settles normally.
    """
    attempts: list[int] = []

    def play(*, sub_game_number: int, role: str, log_path: Path, seed: int) -> dict[str, Any]:
        attempts.append(sub_game_number)
        queued = script.get(sub_game_number)
        if queued:
            return queued.pop(0)
        sub_game_log(
            log_path,
            role=role,
            claim="survival",
            outcome="thief_survival",
            steps=3,
            sub=sub_game_number,
        )
        return {"outcome": "thief_survival", "steps": 3, "audit_ok": True}

    run_live_series(
        rehearsal_sdk(),
        natural_role="police",
        opponent_group=OPPONENT,
        log_dir=tmp_path / "logs",
        out_root=tmp_path / "out",
        seed=7,
        play=play,
        email_transport=RecordingMail(),
    )
    return attempts


_FAILED = {"outcome": HANDSHAKE_FAILED, "steps": 0, "audit_ok": False, "peer_sub_game": None}


def test_a_failed_handshake_is_retried_at_the_same_index(tmp_path: Path) -> None:
    attempts = _drive(tmp_path, {2: [dict(_FAILED), dict(_FAILED)]})
    assert attempts[:5] == [1, 2, 2, 2, 3], attempts
    assert attempts.count(2) == 3  # two failures, then the settling attempt


def test_the_driver_catches_up_to_a_peer_that_is_ahead(tmp_path: Path) -> None:
    """The exact uoh-sqak shape: our window never became a game, and the opponent kept
    declaring an index we had already fallen behind. Holding forever would deadlock."""
    attempts = _drive(tmp_path, {2: [{**_FAILED, "peer_sub_game": 4}]})
    assert attempts[:3] == [1, 2, 4], attempts
    assert 3 not in attempts  # sub-game 3 was settled on THEIR side; we cannot un-play it


def test_a_window_that_never_became_a_game_leaves_no_row(tmp_path: Path) -> None:
    """A series record must describe sub-games that happened. A failed handshake row
    would be a phantom game in a report that both teams have to agree on."""
    attempts: list[int] = []

    def play(*, sub_game_number: int, role: str, log_path: Path, seed: int) -> dict[str, Any]:
        attempts.append(sub_game_number)
        if sub_game_number == 2 and attempts.count(2) == 1:
            return dict(_FAILED)
        sub_game_log(
            log_path,
            role=role,
            claim="survival",
            outcome="thief_survival",
            steps=3,
            sub=sub_game_number,
        )
        return {"outcome": "thief_survival", "steps": 3, "audit_ok": True}

    record = run_live_series(
        rehearsal_sdk(),
        natural_role="police",
        opponent_group=OPPONENT,
        log_dir=tmp_path / "logs",
        out_root=tmp_path / "out",
        seed=7,
        play=play,
        email_transport=RecordingMail(),
    )
    numbers = [row["sub_game_number"] for row in record["sub_games"]]
    assert numbers == [1, 2, 3, 4, 5, 6], numbers


def test_a_series_that_stops_early_refuses_to_report(tmp_path: Path) -> None:
    """LIVE DEFECT, uoh-sqak 2026-08-07 00:02: sub-game 3 never became a game, the retry
    budget ran out, the loop stopped — and the driver then built a report from the TWO
    settled games it held and MAILED it (`num_sub_games: 2`, a 27-27 "series tie").

    The completeness check had never been explicit. The old loop always ran exactly
    `num_games` windows, so the artifact builder could only be handed a full set, and its
    own check — does every log I was given settle? — was sufficient by accident. A loop
    that can stop early hands it a set that is consistent and INCOMPLETE, and nothing
    asked how many there should have been.
    """
    mail = RecordingMail()

    def play(*, sub_game_number: int, role: str, log_path: Path, seed: int) -> dict[str, Any]:
        if sub_game_number == 3:
            return dict(_FAILED)  # never becomes a game, whatever the budget allows
        sub_game_log(
            log_path,
            role=role,
            claim="survival",
            outcome="thief_survival",
            steps=3,
            sub=sub_game_number,
        )
        return {"outcome": "thief_survival", "steps": 3, "audit_ok": True}

    record = run_live_series(
        rehearsal_sdk(),
        natural_role="police",
        opponent_group=OPPONENT,
        log_dir=tmp_path / "logs",
        out_root=tmp_path / "out",
        seed=7,
        play=play,
        email_transport=mail,
    )
    assert "refused" in record, record.keys()
    assert mail.sends == []
    assert mail.drafts == []
    assert record["email"] is None

"""The live series ends by reporting itself (M7-4c): play N sub-games, then ONE email.

A friendly is a counted game in every respect except that it is not counted and the
lecturer is not on the report. That makes the series-end email part of the FORMAT rather
than an operator step afterwards: App E rule 32 requires automatic reporting, and rule 35
zeroes BOTH teams when one side's report is missing or contradictory.

These pins are about the DRIVER, not the sender (whose byte contract is pinned in
`tests/unit/infra/test_email_sender.py`): the whole series produces exactly one report,
it is the artifact this run just emitted, and a series that did not finish honestly
produces none at all. The refuse-BEFORE-play path is `test_live_series_preflight.py`.
"""

from __future__ import annotations

from pathlib import Path

from live_series_harness import FRIENDLY, GAME_ID, rehearsal_sdk, run
from series_fixtures import SERIES_LENGTH


def test_a_finished_series_fires_exactly_one_report_email(tmp_path: Path) -> None:
    outcome, mail, _seen = run(rehearsal_sdk(), tmp_path)

    assert outcome["email"]["action"] == "send"
    assert len(mail.sends) == 1  # ONE report for the whole series, never one per game
    sent = mail.sends[0]
    assert sent["to"] == FRIENDLY
    # Body bytes ARE the artifact's bytes, and the artifact rides attached (rule 34).
    result_path = Path(outcome["result_path"])
    assert result_path.name == f"result_{GAME_ID}.json"
    assert sent["body"] == result_path.read_text(encoding="utf-8")
    assert sent["attachment"] == result_path.name
    assert len(outcome["result"]["sub_games"]) == SERIES_LENGTH


def test_roles_alternate_and_every_sub_game_gets_its_own_seed(tmp_path: Path) -> None:
    """F2 alternation, and six sub-games on ONE seed would replay one game six times
    over a deterministic brain — the series varies the seed the way self-play does."""
    sdk = rehearsal_sdk()
    _outcome, _mail, seen = run(sdk, tmp_path)

    assert len(seen) == sdk.constitution.league.num_games  # the SIGNED count, not ours
    assert [(n, role) for n, role, _seed in seen] == [
        (n, "police" if n % 2 else "thief") for n in range(1, SERIES_LENGTH + 1)
    ]
    assert len({seed for _n, _role, seed in seen}) == SERIES_LENGTH


def test_an_unsettled_sub_game_refuses_the_series_and_sends_nothing(tmp_path: Path) -> None:
    """The rehearsal's s6 shape. A report that quietly drops a game is the contradictory
    report rule 35 punishes on BOTH teams — so no report at all is the honest answer."""
    outcome, mail, seen = run(rehearsal_sdk(), tmp_path, hollow=SERIES_LENGTH)

    assert "refused" in outcome
    assert mail.sends == []
    assert mail.drafts == []
    assert outcome["email"] is None
    assert len(seen) == SERIES_LENGTH  # the driver never abandons the series early


def test_logs_are_named_from_the_series_and_survive_as_the_evidence(tmp_path: Path) -> None:
    outcome, _mail, _seen = run(rehearsal_sdk(), tmp_path)
    logs = [Path(p) for p in outcome["logs"]]

    assert [p.name for p in logs] == [
        f"{GAME_ID}_g{n:02d}.jsonl" for n in range(1, SERIES_LENGTH + 1)
    ]
    assert all(p.is_file() for p in logs)


def test_a_report_that_could_not_be_delivered_is_recorded_not_swallowed(tmp_path: Path) -> None:
    """Found in the first live run: the OAuth token file was missing, the mail backend
    raised, and the whole run record — which sub-games were played, where the artifacts
    landed — died with it, leaving only a traceback.

    Under App E rule 32 a report that did not go out is the single most important fact
    the operator can be told, and it is useless without the path of the artifact that
    still has to reach the opponent. So the failure becomes part of the record.
    """
    outcome, mail, _seen = run(
        rehearsal_sdk(), tmp_path, mail_fails_with=FileNotFoundError("token.json")
    )

    assert outcome["email"]["action"] == "failed"
    assert "token.json" in outcome["email"]["reason"]
    assert outcome["email"]["recipients"] == list(FRIENDLY)
    assert mail.sends == []
    # The artifact exists and is named, so the report can still be sent by hand.
    assert Path(outcome["result_path"]).is_file()
    assert len(outcome["result"]["sub_games"]) == SERIES_LENGTH

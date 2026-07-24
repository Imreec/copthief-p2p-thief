"""The live series ends by reporting itself (M7-4c): play N sub-games, then ONE email.

A friendly is a counted game in every respect except that it is not counted and the
lecturer is not on the report. That makes the series-end email part of the FORMAT rather
than an operator step afterwards: App E rule 32 requires automatic reporting, and rule 35
zeroes BOTH teams when one side's report is missing or contradictory.

These pins are about the DRIVER, not the sender (whose byte contract is pinned in
`tests/unit/infra/test_email_sender.py`): the whole series produces exactly one report,
it is the artifact this run just emitted, and a series that did not finish honestly
produces none at all.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from series_fixtures import SERIES_LENGTH, RecordingMail, sub_game_log

from copthief_core.sdk.live_series import run_live_series
from copthief_core.sdk.simulation import SimulationSdk
from copthief_core.shared.config_model import EmailSettings
from copthief_core.shared.run_mode import RunMode

CONFIG = Path("config")
OPPONENT = "anrbj666"
FRIENDLY = ("us@example.test", "them@example.test")
GAME_ID = f"{SimulationSdk(CONFIG).private.group_id}-vs-{OPPONENT}"


def _sdk(*, recipient: tuple[str, ...] = FRIENDLY, lecturer: str = "") -> SimulationSdk:
    """A rehearsal-mode sdk whose ONLY divergence from the committed tree is `[email]`.

    The live method is the same (M6-4): a copy of the config with the mail section
    flipped, so the committed resting state is never edited in order to play a game.
    """
    sdk = SimulationSdk(CONFIG, mode=RunMode.rehearsal())
    sdk.private = replace(
        sdk.private,
        email=EmailSettings(
            enabled=True,
            mode="send",
            recipient=recipient,
            sender="us@example.test",
            token_path="token.json",
            lecturer=lecturer,
        ),
    )
    return sdk


def _run(
    sdk: SimulationSdk,
    tmp_path: Path,
    *,
    hollow: int | None = None,
    mail_fails_with: Exception | None = None,
) -> tuple[dict[str, Any], RecordingMail, list[tuple[int, str, int]]]:
    """Run the driver with a stand-in for the sub-game process, which writes the log the
    real child would leave behind. `hollow` names a sub-game that never settles."""
    seen: list[tuple[int, str, int]] = []
    mail = RecordingMail(fails_with=mail_fails_with)

    def play(*, sub_game_number: int, role: str, log_path: Path, seed: int) -> dict[str, Any]:
        seen.append((sub_game_number, role, seed))
        if sub_game_number == hollow:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text('{"event": "negotiated", "sender": "x"}\n', encoding="utf-8")
            return {"outcome": "timeout", "steps": 0, "audit_ok": False}
        sub_game_log(
            log_path,
            role=role,
            claim="survival",
            outcome="thief_survival",
            steps=3,
            sub=sub_game_number,
        )
        return {"outcome": "thief_survival", "steps": 3, "audit_ok": True}

    outcome = run_live_series(
        sdk,
        natural_role="police",
        opponent_group=OPPONENT,
        log_dir=tmp_path / "logs",
        out_root=tmp_path / "out",
        seed=7,
        play=play,
        email_transport=mail,
    )
    return outcome, mail, seen


def test_a_finished_series_fires_exactly_one_report_email(tmp_path: Path) -> None:
    outcome, mail, _seen = _run(_sdk(), tmp_path)

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
    sdk = _sdk()
    _outcome, _mail, seen = _run(sdk, tmp_path)

    assert len(seen) == sdk.constitution.league.num_games  # the SIGNED count, not ours
    assert [(n, role) for n, role, _seed in seen] == [
        (n, "police" if n % 2 else "thief") for n in range(1, SERIES_LENGTH + 1)
    ]
    assert len({seed for _n, _role, seed in seen}) == SERIES_LENGTH


def test_an_unsettled_sub_game_refuses_the_series_and_sends_nothing(tmp_path: Path) -> None:
    """The rehearsal's s6 shape. A report that quietly drops a game is the contradictory
    report rule 35 punishes on BOTH teams — so no report at all is the honest answer."""
    outcome, mail, seen = _run(_sdk(), tmp_path, hollow=SERIES_LENGTH)

    assert "refused" in outcome
    assert mail.sends == []
    assert mail.drafts == []
    assert outcome["email"] is None
    assert len(seen) == SERIES_LENGTH  # the driver never abandons the series early


def test_a_rehearsal_cannot_reach_the_lecturer_even_if_he_is_configured(tmp_path: Path) -> None:
    """M7-9: `RunMode.rehearsal()` arms the full rulebook and leaves him unreachable —
    the refusal is structural, not a matter of who remembered to edit the recipient."""
    lecturer = "lecturer@example.test"
    outcome, mail, _seen = _run(_sdk(recipient=(lecturer,), lecturer=lecturer), tmp_path)

    assert outcome["email"]["action"] == "refuse"
    assert "counted" in outcome["email"]["reason"]
    assert mail.sends == []
    # The artifacts still exist: refusing to MAIL a report is not refusing to WRITE it.
    assert Path(outcome["result_path"]).is_file()


def test_logs_are_named_from_the_series_and_survive_as_the_evidence(tmp_path: Path) -> None:
    outcome, _mail, _seen = _run(_sdk(), tmp_path)
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
    outcome, mail, _seen = _run(_sdk(), tmp_path, mail_fails_with=FileNotFoundError("token.json"))

    assert outcome["email"]["action"] == "failed"
    assert "token.json" in outcome["email"]["reason"]
    assert outcome["email"]["recipients"] == list(FRIENDLY)
    assert mail.sends == []
    # The artifact exists and is named, so the report can still be sent by hand.
    assert Path(outcome["result_path"]).is_file()
    assert len(outcome["result"]["sub_games"]) == SERIES_LENGTH

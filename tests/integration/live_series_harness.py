"""Shared harness for the live-series driver suites (split at M7-10b for the 150-line rule).

Both `test_live_series_report.py` (the report path) and `test_live_series_preflight.py`
(the refuse-before-play path) drive `run_live_series` with a stand-in for the sub-game
process. One definition of that stand-in, one rehearsal-mode sdk builder (CLAUDE.md §1 #11).
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from series_fixtures import RecordingMail, sub_game_log

from copthief_core.domain.crypto import series_game_id
from copthief_core.sdk.live_series import run_live_series
from copthief_core.sdk.simulation import SimulationSdk
from copthief_core.shared.config_model import EmailSettings
from copthief_core.shared.run_mode import RunMode

CONFIG = Path("config")
OPPONENT = "anrbj666"
FRIENDLY = ("us@example.test", "them@example.test")
# M7-17: derived the same way the driver derives it (sorted pair, kit SPEC §4) — the
# harness must never re-encode a naming convention the code has moved past.
GAME_ID = series_game_id(SimulationSdk(CONFIG).private.group_id, OPPONENT)


def rehearsal_sdk(*, recipient: tuple[str, ...] = FRIENDLY, lecturer: str = "") -> SimulationSdk:
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


def run(
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

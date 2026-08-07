"""Live series driver (M7-4): play the whole series, then report it ONCE.

`sdk/series_run` drives a SELF-PLAY series — two peers in one process over a queue pair.
A live series against another team is different in one decisive way: each sub-game is
its own process (the rolling-window protocol both teams played the 2026-07-24 rehearsal
in), so nothing in the codebase ever spanned the whole series, and the series-end report
had no owner. Every artifact existed; nothing fired them.

This is that owner. It plays `num_games` sub-games with the roles alternating, joins the
archived logs into the counted-shaped artifact set, and sends the ONE report the series
owes — automatically, because App E rule 32 requires it and rule 35 zeroes BOTH teams
when a report is missing (book §9.3: at game end "there is no longer room for human
intervention"). A friendly differs from a counted series only in who receives that
report, never in whether one is produced.

Refusing is part of the contract: if any sub-game never settled, the series emits NO
artifact and sends NO mail — a report that quietly drops a game is exactly the
contradictory report rule 35 punishes.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from copthief_core.domain.crypto import series_game_id
from copthief_core.infra.email_build import build_report_sender
from copthief_core.infra.email_sender import (
    EmailSender,
    EmailTransport,
    ReportUndeliverableError,
)
from copthief_core.report.schemas import result_filename
from copthief_core.report.series_from_logs import series_artifact_from_logs
from copthief_core.report.summary_from_log import SummaryRebuildError
from copthief_core.sdk.series_windows import missing_sub_games, play_windows

if TYPE_CHECKING:
    from copthief_core.sdk.simulation import SimulationSdk

__all__ = ["PlaySubGame", "run_live_series"]

PlaySubGame = Callable[..., dict[str, Any]]
"""Plays one sub-game to settlement, leaving its log at `log_path`.

Called with keywords only: `sub_game_number`, `role`, `log_path`, `seed`. The live
implementation spawns a process (`sdk/subgame_process`); tests inject a stand-in.
"""


def sub_game_log_path(log_dir: Path, game_id: str, sub_game_number: int) -> Path:
    """Where sub-game `n`'s live log lands — named from the series, so logs from two
    different pairings can never be aggregated into one report by accident."""
    return log_dir / f"{game_id}_g{sub_game_number:02d}.jsonl"


def run_live_series(
    sdk: SimulationSdk,
    *,
    natural_role: str,
    opponent_group: str,
    log_dir: Path,
    out_root: Path,
    seed: int,
    play: PlaySubGame,
    email_transport: EmailTransport | None = None,
) -> dict[str, Any]:
    """Play and report one whole live series (Input: the sdk facade, our natural role,
    the opponent's negotiated group id, where logs and artifacts go, the base seed and
    the sub-game player; Output: the run record — sub-game outcomes, the artifact paths,
    and what the report email actually did).

    The sub-game count comes from the SIGNED constitution, never from the operator: it
    is a negotiated term, and App F fixes it at six for counted play.
    """
    game_id = series_game_id(sdk.private.group_id, opponent_group)
    sender = build_report_sender(
        private=sdk.private,
        limits=sdk.rate_limits,
        transport=email_transport,
        # M7-9: the run's OWN governance decides this, not the recipient list.
        lecturer_addressable=sdk.mode.lecturer_addressable,
    )
    # M7-10b: a run that OWES a report refuses to START if it cannot deliver one. A
    # rehearsal is a counted game minus the counting — the auto-fired report is part of
    # the format — so an empty recipient or a stale token is caught here, before six games
    # are played, rather than after the sixth settles (rule 35 makes the late discovery
    # the costliest). A dev run owes nothing and skips this.
    if sdk.mode.strict_rules:
        try:
            sender.preflight()
        except ReportUndeliverableError as problem:
            return {
                "game_id": game_id,
                "sub_games": [],
                "logs": [],
                "email": None,
                "refused": "the report cannot be delivered — refusing to start a series "
                "that would play out and then fail to report",
                "problems": [str(problem)],
            }
    log_dir.mkdir(parents=True, exist_ok=True)
    # M7-43: the index is NOT a for-loop counter — a window where no game happened
    # must not spend a sub-game, and a peer strictly ahead must be followed. The
    # rules are pure (sdk/series_pacing); the loop is sdk/series_windows.
    run = play_windows(
        play=play,
        log_path_for=lambda n: sub_game_log_path(log_dir, game_id, n),
        natural_role=natural_role,
        num_games=sdk.constitution.league.num_games,
        retry_budget=sdk.private.handshake_retry_budget,
        seed=seed,
    )
    played, logs, durations = run.played, run.logs, run.durations

    record: dict[str, Any] = {
        "game_id": game_id,
        "sub_games": played,
        "logs": [str(path) for path in logs],
        "email": None,
    }
    # M7-43b: a report that quietly drops a game is the contradictory report rule 35
    # punishes, so a partial series is refused outright (see series_windows).
    absent = missing_sub_games(played, sdk.constitution.league.num_games)
    if absent:
        record["refused"] = (
            f"only {len(played)} of {sdk.constitution.league.num_games} sub-games "
            "settled — a partial series has no honest report"
        )
        record["problems"] = [f"sub-game {n} never settled" for n in absent]
        return record
    try:
        result = series_artifact_from_logs(
            logs=logs,
            constitution=sdk.constitution,
            private=sdk.private,
            config_dir=sdk.config_dir,
            opponent_group=opponent_group,
            out_root=out_root,
            durations=durations,
            # M7-36 (the 16:00 window's false record): the league bump keys on
            # COUNTED_SERIES, never on strict_rules — a rehearsal runs the full
            # rulebook without counting ("a counted game minus the counting"), and
            # handing this layer the RULES flag is exactly the confusion RunMode
            # exists to remove (its own docstring). The 16:00 friendly artifact
            # claimed a counted first meeting + a diversity reward because of it.
            counted=sdk.mode.counted_series,
        )
    except SummaryRebuildError as problem:
        record["refused"] = "a sub-game never settled — the series has no honest report"
        record["problems"] = [str(problem)]
        return record

    result_path = out_root / sdk.private.group_id / result_filename(game_id)
    record["result"] = result
    record["result_path"] = str(result_path)
    record["email"] = _report(
        sender,
        result_path=result_path,
        role=natural_role,
        recipients=sdk.private.email.recipient,
    )
    return record


def _report(
    sender: EmailSender, *, result_path: Path, role: str, recipients: Sequence[str]
) -> dict[str, Any]:
    """Send the series report, recording a delivery failure instead of raising it.

    A backend that breaks — the first live run of this driver died on a missing OAuth
    token — must not take the run record with it. Under App E rule 32 a report that did
    NOT go out is the most important thing the operator can be told, and the telling is
    useless without the path of the artifact that still has to reach the opponent.
    Broad by intent: every way a mail backend can fail is the same fact here.
    """
    try:
        return sender.send_report(result_path=result_path, role=role)
    except Exception as failure:  # noqa: BLE001 - any backend failure is one outcome
        return {
            "action": "failed",
            "reason": f"{type(failure).__name__}: {failure}",
            "recipients": list(recipients),
            "result_path": str(result_path),
        }

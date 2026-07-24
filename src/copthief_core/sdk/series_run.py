"""Local full-series flow (M6-6 DoD; PLAN §13 M6): play, emit, attempt the email.

Two in-process peers play the SIGNED `num_games` with role alternation over one
persistent queue-transport pair. Self-play honesty: the mirror side runs under a
clearly-labeled "-mirror" identity (PRD_reporting §6) — the declaration states
exactly what happened. The natural side emits all artifacts and then attempts the
report email through the full interlock+gatekeeper rail (shipped resting state:
refuse — constraint #16 observed end-to-end).
"""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from copthief_core.domain.terms import terms_from_config
from copthief_core.infra.email_sender import EmailTransport, build_report_sender
from copthief_core.peer.match import _locked_log
from copthief_core.peer.sealing import live_spec_record
from copthief_core.peer.series import run_peer_series
from copthief_core.peer.session import PeerSession
from copthief_core.peer.settlement import PeerGameResult
from copthief_core.peer.transport import queue_pair
from copthief_core.report.emit import emit_series
from copthief_core.report.schemas import result_filename
from copthief_core.sdk.identity import identity_block
from copthief_core.shared.config import load_all, load_gazetteer
from copthief_core.shared.config_model import Constitution, PrivateSettings


def _side(
    constitution: Constitution,
    private: PrivateSettings,
    *,
    natural_role: str,
    base_seed: int,
    gazetteer: Any,  # noqa: ANN401 - optional Gazetteer
    transport: Any,  # noqa: ANN401 - PeerTransport protocol
    logs: dict[int, Any],
) -> list[tuple[PeerGameResult, dict[str, Any]]]:
    """One peer's whole series (runs on its own thread)."""

    def make_session(n: int, role: str, hint_trust: float | None) -> PeerSession:
        return PeerSession(
            constitution,
            private,
            role=role,
            seed=base_seed + n,
            gazetteer=gazetteer,
            hint_trust=hint_trust,
            spec_record=live_spec_record(private, constitution, sub_game_number=n),
        )

    return run_peer_series(
        num_games=constitution.league.num_games,
        natural_role=natural_role,
        make_session=make_session,
        transport=transport,
        turn_timeout=private.turn_timeout_seconds,
        poll_interval=private.poll_interval_seconds,
        log_factory=lambda n: logs[n],
    )


def run_local_series(
    config_dir: Path,
    *,
    base_police_seed: int,
    base_thief_seed: int,
    out_root: Path,
    log_dir: Path,
    email_transport: EmailTransport | None = None,
) -> dict[str, Any]:
    """The M6-6 exit flow (Input: config tree + seeds + output roots; Output:
    result artifact + both sides' settlement results + the email outcome)."""
    constitution, private, limits = load_all(config_dir, counted=False)
    gazetteer = load_gazetteer(
        config_dir / "gazetteer.json",
        map_area=constitution.world.map_area,
        board=constitution.board.make_board(),
    )
    mirror = replace(
        private,
        group_id=f"{private.group_id}-mirror",
        group_name=f"{private.group_name} (mirror)",
    )
    log_dir.mkdir(parents=True, exist_ok=True)
    logs = {
        n: _locked_log(log_dir / f"series_g{n:02d}.jsonl")
        for n in range(1, constitution.league.num_games + 1)
    }
    natural_transport, mirror_transport = queue_pair(wait_timeout=private.connect_timeout_seconds)
    sides: dict[str, list[tuple[PeerGameResult, dict[str, Any]]]] = {}

    def play(name: str, who: PrivateSettings, role: str, seed: int, transport: Any) -> None:  # noqa: ANN401
        sides[name] = _side(
            constitution,
            who,
            natural_role=role,
            base_seed=seed,
            gazetteer=gazetteer,
            transport=transport,
            logs=logs,
        )

    threads = [
        threading.Thread(
            target=play,
            args=("natural", private, "police", base_police_seed, natural_transport),
            name="series-natural",
        ),
        threading.Thread(
            target=play,
            args=("mirror", mirror, "thief", base_thief_seed, mirror_transport),
            name="series-mirror",
        ),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=private.turn_timeout_seconds + private.connect_timeout_seconds)

    summaries = [summary for _result, summary in sides["natural"]]
    result = emit_series(
        summaries=summaries,
        own_identity=identity_block(private),
        opponent_identity=identity_block(mirror),
        game_id=f"{private.group_id}-vs-{mirror.group_id}",
        game_uid=sides["natural"][0][0].game_uid,
        shared_terms=json.loads((config_dir / "game.json").read_text(encoding="utf-8")),
        terms=terms_from_config(constitution),
        table=constitution.scoring,
        out_root=out_root,
    )
    sender = build_report_sender(
        private=private,
        limits=limits,
        transport=email_transport,
        # M7-9: self-play is never a counted series, so the lecturer is unreachable from
        # here by construction rather than by remembering to say so.
        lecturer_addressable=False,
    )
    email = sender.send_report(
        result_path=out_root / private.group_id / result_filename(result["game_id"]),
        role="police",
    )
    return {
        "result": result,
        "group_id": private.group_id,
        "email": email,
        "natural_results": [asdict(r) for r, _s in sides["natural"]],
        "mirror_results": [asdict(r) for r, _s in sides["mirror"]],
    }

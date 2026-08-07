"""CLI entry (TODO M1-7): everything goes through SimulationSdk, output is JSON/ASCII.

Commands:
  copthief run local-match   one command, full mini-game, both peers in-process (queues)
  copthief run p2p-match     one command, full mini-game, TWO processes over localhost HTTP
  copthief run peer          play one full standalone peer (own server + symmetric loop)
                             --sub-game N seals the real series index (rules 37-38)
                             --sparring refuses a config carrying tuned weights or mail
  copthief series            play a WHOLE live series, then auto-send its ONE report
  copthief replay            re-verify a JSONL log -> Verified OK / TAMPERED (M4-3)

`--rehearsal` / `--counted` arm the App F rulebook; only `--counted` can address the
lecturer (M7-9). `replay` exits 0 on Verified OK and 1 on TAMPERED. `series` exits 2 when
it refuses to report a series that never settled, and 3 when the report exists but could
not be delivered — different failures, different next actions (script/CI-friendly).
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from copthief_core.peer.p2p import PeerGameResult
from copthief_core.sdk.cli_args import build_parser, run_mode_from_args
from copthief_core.sdk.simulation import SimulationSdk
from copthief_core.shared.sparring import sparring_problems

_parser = build_parser  # kept as the historical spelling used by the CLI tests


def _run_series(sdk: SimulationSdk, args: argparse.Namespace) -> int:
    """Play and report one live series; exit 2 if it has no honest report to send."""
    from copthief_core.sdk.live_series import run_live_series
    from copthief_core.sdk.series_endpoints import endpoints_from_flags
    from copthief_core.sdk.subgame_process import subgame_player

    port: int = args.port if args.port is not None else sdk.private.my_port
    endpoints = endpoints_from_flags(
        single=args.opponent_url,
        police_url=args.opponent_police_url,
        thief_url=args.opponent_thief_url,
        config_default=sdk.private.opponent_url,
    )
    record = run_live_series(
        sdk,
        natural_role=args.role,
        opponent_group=args.opponent_group,
        log_dir=args.log_dir,
        out_root=args.out,
        seed=args.seed,
        play=subgame_player(
            config_dir=sdk.config_dir,
            host=args.host,
            port=port,
            endpoints=endpoints,
            mode=sdk.mode,
            opponent_group=args.opponent_group,
        ),
    )
    # The whole result artifact is on disk and would drown the console; the run record
    # names it instead, and carries what the operator must see: what each sub-game did
    # and what the report email actually did.
    print(json.dumps({k: v for k, v in record.items() if k != "result"}, ensure_ascii=False))
    if "refused" in record:
        return 2  # the series produced no report at all
    # Distinct on purpose: an artifact that exists but did not reach the opponent needs a
    # different action from one that was never written (App E rule 32 either way).
    return 3 if (record.get("email") or {}).get("action") == "failed" else 0


def main(argv: list[str] | None = None) -> int:
    """Dispatch one CLI invocation; every flow prints one JSON object."""
    args = build_parser().parse_args(argv)
    sdk = SimulationSdk(args.config, mode=run_mode_from_args(args))
    if args.verb == "overlay":
        overlay_png, curve_png = sdk.export_overlay(args.log, args.out, role=args.role)
        print(json.dumps({"overlay": str(overlay_png), "curve": str(curve_png)}))
        return 0
    if args.verb == "replay":
        from copthief_core.peer.replay import verdict_for

        summary = sdk.replay(args.log, gui=args.gui)
        print(
            json.dumps(
                {
                    "verdict": verdict_for(summary),
                    "problems": summary.problems,
                    "steps": summary.steps,
                    "outcome": summary.outcome,
                    "game_uid": summary.game_uid,
                    # M7-7(4): the work behind the verdict, on the face of it — a
                    # "Verified OK" over zero records is what the guard now refuses.
                    "records_verified": summary.records_verified,
                },
                ensure_ascii=False,
            )
        )
        return 0 if summary.verified else 1
    if args.verb == "series":
        return _run_series(sdk, args)
    if args.flow == "local-match":
        result = sdk.run_local_match(
            police_seed=args.police_seed,
            thief_seed=args.thief_seed,
            log_path=args.log,
            gui=args.gui,
        )
        payload = {k: v for k, v in asdict(result).items() if not k.endswith("_moves")}
        payload["police_state"] = result.police_state.value
        payload["thief_state"] = result.thief_state.value
        print(json.dumps(payload))
        return 0
    if args.flow == "p2p-match":
        thief_port = args.thief_port if args.thief_port is not None else sdk.private.my_port + 1
        p2p_result = sdk.run_p2p_match(
            police_seed=args.police_seed,
            thief_seed=args.thief_seed,
            thief_port=thief_port,
            host=args.host,
        )
        print(json.dumps(asdict(p2p_result)))
        return 0
    if args.sparring:
        # M7-1: the standing-host rules are asserted at the moment of use, not
        # remembered — a peer stood up for an opponent to practise against may not carry
        # tuned weights (CLAUDE.md §9) and may not be able to send mail (ADR-0008 §6).
        # The refusal is a normal JSON result, not a traceback: this is an expected
        # answer to a wrong config, and it must be readable in an ops window.
        problems = sparring_problems(sdk.private)
        if problems:
            print(json.dumps({"refused": "sparring-unsafe config", "problems": problems}))
            return 2
    port = args.port if args.port is not None else sdk.private.my_port
    opponent_url = args.opponent_url if args.opponent_url is not None else sdk.private.opponent_url
    from copthief_core.peer.handshake import NegotiationError
    from copthief_core.peer.port_guard import PeerAlreadyRunningError
    from copthief_core.sdk.series_pacing import handshake_failed_result

    try:
        peer_result = _play_peer(sdk, args, port=port, opponent_url=opponent_url)
    except PeerAlreadyRunningError as refusal:
        # M7-10: an expected answer to a contended port, so it reads like the --sparring
        # refusal — one JSON object and exit 2, never a traceback in an ops window. The
        # series driver parses this and records WHICH sub-game did not start, and why.
        print(json.dumps({"refused": "another live peer holds this role", "why": str(refusal)}))
        return 2
    except NegotiationError as failed:
        # M7-43: a window where NO GAME HAPPENED is a first-class result, not a dead
        # child. Reported so the series driver can hold the index and retry, and
        # carrying whatever index the opponent declared so it can catch up instead of
        # deadlocking on a number they have already left behind.
        print(json.dumps(handshake_failed_result(str(failed), failed.peer_sub_game)))
        return 2
    print(json.dumps(asdict(peer_result)))
    return 0


def _play_peer(
    sdk: SimulationSdk, args: argparse.Namespace, *, port: int, opponent_url: str
) -> PeerGameResult:
    """One standalone peer, with the CLI's defaults already resolved."""
    return sdk.run_peer(
        role=args.role,
        seed=args.seed,
        host=args.host,
        port=port,
        opponent_url=opponent_url,
        log_path=args.log,
        gui=args.gui,
        sub_game_number=args.sub_game,
        opponent_group=args.opponent_group,
    )


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main"]

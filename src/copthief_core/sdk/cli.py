"""CLI entry (TODO M1-7): everything goes through SimulationSdk, output is JSON/ASCII.

Commands:
  copthief run local-match   one command, full mini-game, both peers in-process (queues)
  copthief run p2p-match     one command, full mini-game, TWO processes over localhost HTTP
  copthief run peer          play one full standalone peer (own server + symmetric loop)
                             --sub-game N seals the real series index (rules 37-38)
                             --sparring refuses a config carrying tuned weights or mail
  copthief replay            re-verify a JSONL log -> Verified OK / TAMPERED (M4-3)

`replay` exits 0 on Verified OK and 1 on TAMPERED (script/CI-friendly).
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from copthief_core.sdk.simulation import SimulationSdk
from copthief_core.shared.sparring import sparring_problems

_LOCALHOST = "127.0.0.1"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="copthief")
    commands = parser.add_subparsers(dest="verb", required=True)
    run = commands.add_parser("run", help="run a game flow")
    flows = run.add_subparsers(dest="flow", required=True)

    local = flows.add_parser("local-match", help="in-process mini-game over queue transports")
    p2p = flows.add_parser("p2p-match", help="two-process mini-game over localhost FastMCP")
    peer = flows.add_parser("peer", help="play one standalone peer (blocking, full game)")

    for sub in (local, p2p, peer):
        sub.add_argument("--config", type=Path, default=Path("config"))
    for sub in (local, p2p):
        sub.add_argument("--police-seed", type=int, default=11)
        sub.add_argument("--thief-seed", type=int, default=22)
    for sub in (local, peer):
        sub.add_argument("--log", type=Path, default=None, help="write a replayable JSONL log")
        sub.add_argument(
            "--gui", action="store_true", help="open the live view (belief heatmap + turn banner)"
        )
    p2p.add_argument("--host", default=_LOCALHOST)
    p2p.add_argument("--thief-port", type=int, default=None, help="default: my_port + 1")
    peer.add_argument("--role", required=True, choices=("police", "thief"))
    peer.add_argument("--seed", type=int, default=22)
    peer.add_argument("--host", default=_LOCALHOST)
    peer.add_argument("--port", type=int, default=None, help="default: game.toml my_port")
    peer.add_argument(
        "--opponent-url", default=None, help="default: game.toml network.opponent_url"
    )
    peer.add_argument(
        "--sub-game",
        type=int,
        default=None,
        help="which sub-game of the series this is; sealed into the step-0 declaration "
        "(rules 37-38). Omit for a one-off game -- a SERIES must pass the real index.",
    )
    peer.add_argument(
        "--sparring",
        action="store_true",
        help="refuse to play unless the config is safe for a standing host "
        "(no tuned weights, no mail) -- CLAUDE.md s9, ADR-0008 s6",
    )
    replay = commands.add_parser("replay", help="re-verify a JSONL log (Verified OK / TAMPERED)")
    replay.add_argument("--log", type=Path, required=True, help="the JSONL game log to verify")
    replay.add_argument("--config", type=Path, default=Path("config"))
    replay.add_argument("--gui", action="store_true", help="open the step-through viewer")
    overlay = commands.add_parser(
        "overlay", help="render belief-vs-truth overlay + error-curve PNGs (post-audit)"
    )
    overlay.add_argument("--log", type=Path, required=True, help="an AUDITED JSONL game log")
    overlay.add_argument("--out", type=Path, required=True, help="overlay PNG path")
    overlay.add_argument("--role", choices=("police", "thief"), default=None)
    overlay.add_argument("--config", type=Path, default=Path("config"))
    return parser


def main(argv: list[str] | None = None) -> int:
    """Dispatch one CLI invocation; every flow prints one JSON object."""
    args = _parser().parse_args(argv)
    sdk = SimulationSdk(args.config)
    if args.verb == "overlay":
        overlay_png, curve_png = sdk.export_overlay(args.log, args.out, role=args.role)
        print(json.dumps({"overlay": str(overlay_png), "curve": str(curve_png)}))
        return 0
    if args.verb == "replay":
        from copthief_core.peer.replay import verdict_for

        summary = sdk.replay(args.log, gui=args.gui)
        verdict = verdict_for(summary)
        print(
            json.dumps(
                {
                    "verdict": verdict,
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
    peer_result = sdk.run_peer(
        role=args.role,
        seed=args.seed,
        host=args.host,
        port=port,
        opponent_url=opponent_url,
        log_path=args.log,
        gui=args.gui,
        sub_game_number=args.sub_game,
    )
    print(json.dumps(asdict(peer_result)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

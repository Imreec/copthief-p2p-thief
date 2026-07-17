"""CLI entry (TODO M1-7): everything goes through SimulationSdk, output is JSON/ASCII.

Commands:
  copthief run local-match   one command, full mini-game, both peers in-process (queues)
  copthief run p2p-match     one command, full mini-game, TWO processes over localhost HTTP
  copthief run peer          play one full standalone peer (own server + symmetric loop)
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from copthief_core.sdk.simulation import SimulationSdk

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
    p2p.add_argument("--host", default=_LOCALHOST)
    p2p.add_argument("--thief-port", type=int, default=None, help="default: my_port + 1")
    peer.add_argument("--role", required=True, choices=("police", "thief"))
    peer.add_argument("--seed", type=int, default=22)
    peer.add_argument("--host", default=_LOCALHOST)
    peer.add_argument("--port", type=int, default=None, help="default: game.toml my_port")
    peer.add_argument(
        "--opponent-url", default=None, help="default: game.toml network.opponent_url"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Dispatch one CLI invocation; every flow prints one JSON object."""
    args = _parser().parse_args(argv)
    sdk = SimulationSdk(args.config)
    if args.flow == "local-match":
        result = sdk.run_local_match(
            police_seed=args.police_seed, thief_seed=args.thief_seed, log_path=args.log
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
    port = args.port if args.port is not None else sdk.private.my_port
    opponent_url = args.opponent_url if args.opponent_url is not None else sdk.private.opponent_url
    peer_result = sdk.run_peer(
        role=args.role,
        seed=args.seed,
        host=args.host,
        port=port,
        opponent_url=opponent_url,
        log_path=args.log,
    )
    print(json.dumps(asdict(peer_result)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

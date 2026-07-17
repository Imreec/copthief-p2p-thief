"""CLI entry (TODO M1-7): everything goes through SimulationSdk, output is JSON/ASCII.

Commands:
  copthief run local-match   one command, full mini-game, both peers in-process (fake MCP)
  copthief run p2p-match     one command, full mini-game, TWO processes over localhost HTTP
  copthief run peer          serve one peer's tools (used by p2p-match's subprocess)
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
    run = commands.add_parser("run", help="run an M1 flow")
    flows = run.add_subparsers(dest="flow", required=True)

    local = flows.add_parser("local-match", help="in-process mini-game over the MCP fake")
    p2p = flows.add_parser("p2p-match", help="two-process mini-game over localhost FastMCP")
    peer = flows.add_parser("peer", help="serve one peer's four tools (blocking)")

    for sub in (local, p2p, peer):
        sub.add_argument("--config", type=Path, default=Path("config"))
    for sub in (local, p2p):
        sub.add_argument("--police-seed", type=int, default=11)
        sub.add_argument("--thief-seed", type=int, default=22)
    local.add_argument("--log", type=Path, default=None, help="write a replayable JSONL log")
    p2p.add_argument("--host", default=_LOCALHOST)
    p2p.add_argument("--thief-port", type=int, default=None, help="default: my_port + 1")
    peer.add_argument("--role", required=True, choices=("police", "thief"))
    peer.add_argument("--seed", type=int, default=22)
    peer.add_argument("--host", default=_LOCALHOST)
    peer.add_argument("--port", type=int, default=None, help="default: game.toml my_port")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Dispatch one CLI invocation; match results print as one JSON object."""
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
    sdk.serve_peer(role=args.role, seed=args.seed, host=args.host, port=port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""CLI surface (split from sdk/cli at M7-4 for the 150-line rule).

Holds the argument grammar and the one mapping that must not be improvised: command-line
flags to `RunMode`. `--rehearsal` arms the full App F rulebook while leaving the lecturer
structurally unreachable; `--counted` is the only thing that can address him at all, and
it cannot be constructed without the rules armed (M7-9 / ADR-0009).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from copthief_core.shared.run_mode import RunMode

_LOCALHOST = "127.0.0.1"


def run_mode_from_args(args: argparse.Namespace) -> RunMode:
    """The run's governance, read from the parsed flags (Input: the namespace; Output:
    the RunMode — dev by default, because nothing is armed unless it is asked for)."""
    if getattr(args, "counted", False):
        return RunMode.counted()
    return RunMode.rehearsal() if getattr(args, "rehearsal", False) else RunMode()


def _add_governance(parser: argparse.ArgumentParser) -> None:
    """Attach the two mutually-exclusive governance flags to a flow."""
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--rehearsal",
        action="store_true",
        help="play under the FULL App F rulebook (a real six-mini-game constitution) "
        "with the lecturer structurally unreachable -- a friendly is a counted game "
        "minus the counting",
    )
    group.add_argument(
        "--counted",
        action="store_true",
        help="a counted league series: the full rulebook AND the only mode from which "
        "the lecturer may be a configured recipient",
    )


def build_parser() -> argparse.ArgumentParser:
    """The whole CLI grammar (Output: the parser; every flow prints one JSON object)."""
    parser = argparse.ArgumentParser(prog="copthief")
    commands = parser.add_subparsers(dest="verb", required=True)
    run = commands.add_parser("run", help="run a game flow")
    flows = run.add_subparsers(dest="flow", required=True)

    local = flows.add_parser("local-match", help="in-process mini-game over queue transports")
    p2p = flows.add_parser("p2p-match", help="two-process mini-game over localhost FastMCP")
    peer = flows.add_parser("peer", help="play one standalone peer (blocking, full game)")
    series = commands.add_parser(
        "series", help="play a whole live series, then send its ONE report (M7-4)"
    )

    for sub in (local, p2p, peer, series):
        sub.add_argument("--config", type=Path, default=Path("config"))
    for sub in (local, p2p):
        sub.add_argument("--police-seed", type=int, default=11)
        sub.add_argument("--thief-seed", type=int, default=22)
    for sub in (local, peer):
        sub.add_argument("--log", type=Path, default=None, help="write a replayable JSONL log")
        sub.add_argument(
            "--gui", action="store_true", help="open the live view (belief heatmap + turn banner)"
        )
    for sub in (peer, series):
        sub.add_argument("--role", required=True, choices=("police", "thief"))
        sub.add_argument("--host", default=_LOCALHOST)
        sub.add_argument("--port", type=int, default=None, help="default: game.toml my_port")
        sub.add_argument(
            "--opponent-url", default=None, help="default: game.toml network.opponent_url"
        )
        _add_governance(sub)

    p2p.add_argument("--host", default=_LOCALHOST)
    p2p.add_argument("--thief-port", type=int, default=None, help="default: my_port + 1")
    peer.add_argument("--seed", type=int, default=22)
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
    _series_options(series)

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


def _series_options(series: argparse.ArgumentParser) -> None:
    """The live-series flow's own arguments (`--role` is the NATURAL role: F2 gives it
    the odd sub-games, and the opponent takes the same role on the even ones)."""
    series.add_argument(
        "--opponent-group",
        required=True,
        help="the opponent's negotiated group id -- it names the series in every "
        "artifact, so both teams' reports can be matched to one game_id",
    )
    series.add_argument(
        "--seed", type=int, default=22, help="base seed; each sub-game adds its index"
    )
    series.add_argument("--log-dir", type=Path, default=Path("logs"))
    series.add_argument(
        "--out", type=Path, default=Path("reports"), help="where the artifact set is written"
    )

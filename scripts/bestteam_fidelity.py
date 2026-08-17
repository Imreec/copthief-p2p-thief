"""Validate the bestteam-thief mimic against the 2026-08-16 friendly tapes (M13p2).

Per their move in our cop games (g02/g04/g06): reconstruct the inputs their brain
saw (their belief of our cop, their own trail, the board), ask the mimic, compare.
Two honest numbers per game: STRICT argmax agreement, and TIE-AWARE agreement (their
move inside the mimic's tie window — draws are seeded RNG we cannot align).

Belief reconstruction (golden-oracle finding, 2026-08-17): their belief runs on our
scent TWO steps stale (they move first, so our newest revealed frame is a turn old
and can be nothing else - their own docstring), and barriers lag ONE step. All three
games ran their FIXED subtractive kernel; sharpness is ~equal across games (peak
mass ~0.6). Reconstructed here as a delta at our step-(k-2) cell (steps 1-2:
uniform minus their own cell - nothing revealed yet).

Usage: uv run python scripts/bestteam_fidelity.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "src")

from copthief_core.domain.board import Board  # noqa: E402
from copthief_core.strategy.bestteam_thief import THIEF_DEFAULTS, BestteamThiefBrain  # noqa: E402
from copthief_core.strategy.brains import Observation  # noqa: E402

MOVE_SET = ("N", "S", "E", "W", "STAY")
RINGS = (0.9, 0.6, 0.3)  # their fixed subtractive emission (HEAD a59fa05)
DECAY = 0.1


class _FixedBelief:
    """Duck-typed belief handing the mimic a reconstructed posterior."""

    def __init__(self, probs: dict[tuple[int, int], float]) -> None:
        self._probs = probs

    def probs(self) -> dict[tuple[int, int], float]:
        return dict(self._probs)


def _trail(path: list[tuple[int, int]]) -> dict[str, float]:
    """Their own trail field over their walked path (deposit rings, subtract-decay)."""
    field: dict[tuple[int, int], float] = {}
    for pos in path:
        for r in range(-2, 3):
            for c in range(-2, 3):
                cell = (pos[0] + r, pos[1] + c)
                if 0 <= cell[0] <= 6 and 0 <= cell[1] <= 6:
                    ring = max(abs(r), abs(c))
                    field[cell] = max(field.get(cell, 0.0), RINGS[ring] if ring < 3 else 0.0)
        field = {c: round(v - DECAY, 3) for c, v in field.items() if v - DECAY > 0.0}
    return {f"{c[0]},{c[1]}": v for c, v in field.items()}


def _game(n: int) -> tuple[dict, dict, list]:
    events = [
        json.loads(line)
        for line in Path(f"logs/bestteam-vs-imreeyal_g{n:02d}.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    audit = next(e for e in events if e.get("event") == "audit")
    mine = {
        r["payload"]["step"]: tuple(r["payload"]["position"])
        for r in audit["payload"]["records"]
        if "position" in r.get("payload", {}) and "step" in r["payload"]
    }
    received = next(e for e in events if e.get("event") == "audit_received")
    theirs = {
        r["payload"]["step"]: (tuple(r["payload"]["position"]), r["payload"].get("move"))
        for r in received["raw"]["records"]
        if "position" in r.get("payload", {})
    }
    walls = [
        (e["raw"]["step"], tuple(e["raw"]["barrier_placed"]))
        for e in events
        if e.get("event") == "turn" and (e.get("raw") or {}).get("barrier_placed")
    ]
    return mine, theirs, walls


def _belief(mode: str, cop: tuple[int, int] | None, own: tuple[int, int]) -> _FixedBelief:
    del mode
    if cop is None:  # steps 1-2: nothing of ours revealed to them yet
        cells = [(r, c) for r in range(7) for c in range(7) if (r, c) != own]
        return _FixedBelief({c: 1.0 / len(cells) for c in cells})
    return _FixedBelief({cop: 1.0})


def main() -> int:
    for n, mode in ((2, "lag2"), (4, "lag2"), (6, "lag2")):
        mine, theirs, walls = _game(n)
        strict = tie_aware = total = 0
        for s in sorted(theirs):
            if s + 1 not in theirs or s not in mine:
                continue
            pos, _ = theirs[s]
            actual = theirs[s + 1][1]
            board = Board(
                grid_size=7,
                axis_origin_corner="top-left",
                axis_start_index=0,
                # barriers lag ONE step behind their decision (oracle finding)
                barriers=frozenset(c for ws, c in walls if ws <= s - 1),
            )
            path = [theirs[k][0] for k in sorted(theirs) if k <= s]
            obs = Observation(
                board=board,
                position=pos,
                move_set=MOVE_SET,
                role="thief",
                step=s,
                barriers_used=0,
                max_barriers=14,
                own_smell=_trail(path),
            )
            brain = BestteamThiefBrain(seed=1)
            lagged_cop = mine.get(s - 2)  # our cell as their two-step-stale scent names it
            chosen = brain.pick_move(obs, _belief(mode, lagged_cop, pos))  # type: ignore[arg-type]
            near = _near_set(brain, obs, _belief(mode, lagged_cop, pos))
            total += 1
            strict += chosen == actual
            tie_aware += actual in near
        pct = 100 * tie_aware / total
        print(
            f"g{n:02d} [{mode:7s}]: strict {strict}/{total}  tie-aware {tie_aware}/{total} ({pct:.0f}%)"
        )
    return 0


def _near_set(brain: BestteamThiefBrain, obs: Observation, belief: _FixedBelief) -> list[str]:
    opts = {**THIEF_DEFAULTS, **{}}
    board, here = obs.board, obs.position
    scored = []
    for move in ("STAY", "N", "S", "E", "W"):
        dest = board.apply_move(here, move)
        if move != "STAY" and (dest == here or board.is_blocked(dest)):
            continue
        value = brain._value_of(  # noqa: SLF001 - fidelity harness reads the seam
            dest, belief.probs(), board, 14 - len(board.barriers), 2, opts
        ) - opts["weight_scent"] * float(obs.own_smell.get(f"{dest[0]},{dest[1]}", 0.0))
        scored.append((value, move))
    best = max(v for v, _ in scored)
    return [m for v, m in scored if best - v <= opts["tie_epsilon"]]


if __name__ == "__main__":
    raise SystemExit(main())

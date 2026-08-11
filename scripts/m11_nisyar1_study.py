"""nis-yar1 friendly postmortem (2026-08-11 logs) — throwaway instrument, not CI.

Prints, per game: both tracks (ours from decisions, theirs from their audit's
revealed positions), our belief argmax vs their true cell (odd games), and wall
placements — the g01 conversion-failure postmortem and the g02/g04/g06 cage
study the M11 session prompt update asked for.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

LOG_DIR = Path("docs/evidence/friendly-nis-yar1-2026-08-11")


def load(game: str) -> list[dict]:
    path = LOG_DIR / f"imreeyal-vs-nis-yar1_{game}.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def their_track(events: list[dict]) -> list[tuple[int, tuple[int, int], object]]:
    """(step, revealed position, barrier) per record of THEIR audit."""
    audit = next(e for e in events if e["event"] == "audit_received")
    rows = []
    for record in audit["raw"]["records"]:
        payload = record["payload"]
        pos = payload.get("position") or payload.get("state")
        if pos is None or "step" not in payload:
            continue
        rows.append((payload["step"], tuple(pos), payload.get("barrier")))
    return rows


def our_moves(events: list[dict]) -> list[tuple[int, str, object]]:
    out = []
    for e in events:
        if e["event"] == "decision":
            out.append((e["payload"]["step"], e["payload"]["move"], e["payload"].get("barrier")))
    return out


def our_beliefs(events: list[dict]) -> dict[int, str]:
    return {e["payload"]["step"]: e["payload"]["argmax"] for e in events if e["event"] == "belief"}


def outbound_barriers(events: list[dict]) -> dict[int, object]:
    walls = {}
    step = 0
    for e in events:
        if e["event"] == "turn":
            step += 1
            placed = e["message"].get("barrier_placed")
            if placed is not None:
                walls[step] = placed
    return walls


def study(game: str) -> None:
    events = load(game)
    theirs = their_track(events)
    ours = our_moves(events)
    beliefs = our_beliefs(events)
    walls = outbound_barriers(events)
    result = next((e for e in events if e["event"] == "peer_result"), {})
    print(f"== {game}: {json.dumps(result.get('payload', result.get('raw', '?')))[:120]}")
    print(f"   our walls at steps: {walls}")
    track = {step: pos for step, pos, _b in theirs}
    their_walls = {step: b for step, _p, b in theirs if b}
    if their_walls:
        print(f"   their walls: {their_walls}")
    hits = misses = 0
    for step, pos in sorted(track.items()):
        argmax = beliefs.get(step)
        if argmax is None:
            continue
        if argmax == f"{pos[0]},{pos[1]}":
            hits += 1
        else:
            misses += 1
    if hits or misses:
        print(f"   belief argmax == their cell: {hits}/{hits + misses}")
    print("   theirs:", " ".join(f"{s}:{p}" for s, p in sorted(track.items())))
    print("   ours  :", " ".join(f"{s}:{m}{'+W' + str(b) if b else ''}" for s, m, b in ours))


if __name__ == "__main__":
    for game in sys.argv[1:] or ["g01", "g02", "g04", "g06"]:
        study(game)

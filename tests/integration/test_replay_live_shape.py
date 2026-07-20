"""M7-7(4): replay must read the LIVE log shape, and must never pass vacuously.

A live peer log emits `peer_result` (peer/settlement) — `result` is the *local*
two-sided match event (peer/match). `replay_from_log` only ever read `result`, so every
real game — every friendly, every tunnel run, the mandatory README screenshot — rendered
`steps 0 / outcome unknown / game_uid ""` while the verdict underneath was computed
correctly. The live shape carries no `game_uid` in its result payload either: it is
established at the handshake, so the `negotiated` event is the source.

Rider (the more dangerous half): `verified = not problems` is TRUE when nothing was
checked, so a truncated or empty log printed "Verified OK". A replay that verified zero
records now says TAMPERED — fail-closed, like every other rule-19 surface.

This test is MIRRORED, so it names no role-specific evidence file (portable-pin lesson,
PR #29): it globs THIS repo's own committed live-peer log — the cop's M5 friendly, the
thief's M3 full-pairing, both Verified OK. The cop's exact-number pin lives in the
non-mirrored `tests/role/`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from copthief_core.peer.match import run_local_minigame
from copthief_core.peer.replay import (
    VERDICT_OK,
    VERDICT_TAMPERED,
    replay_from_log,
    verdict_for,
)
from copthief_core.shared.jsonl_logger import read_events

EVIDENCE = Path("docs/evidence")


def a_live_peer_log() -> Path:
    """A committed live-peer log for THIS repo — one carrying `peer_result` AND its own
    revealed audit (a settled standalone peer game, not a local two-sided match, and not
    a pre-v1.1 log). Globbed so the mirrored test is repo-agnostic — the cop has the M5
    friendly, the thief its M3 full-pairing; skips if a repo has none yet."""
    for path in sorted(EVIDENCE.glob("*.jsonl")):
        kinds = {
            json.loads(line).get("event") for line in path.read_text(encoding="utf-8").splitlines()
        }
        if {"peer_result", "audit"} <= kinds:
            return path
    pytest.skip("no committed live-peer log in this repo")


def test_a_live_peer_log_populates_the_banner() -> None:
    summary = replay_from_log(a_live_peer_log())
    assert verdict_for(summary) == VERDICT_OK
    assert summary.steps > 0  # NOT the old vacuous 0
    assert summary.outcome not in ("", "unknown")
    assert len(summary.game_uid) > 0  # from the handshake, not from the result payload
    assert summary.records_verified >= 1  # NOT vacuously verified over zero records
    # (a repo's own live log may be one-sided — the exact per-side moves are pinned in
    # the non-mirrored cop role test, where the opponent's audit is archived too.)


def test_the_live_game_uid_is_the_negotiated_one() -> None:
    log = a_live_peer_log()
    negotiated = next(e for e in read_events(log) if e["event"] == "negotiated")
    assert replay_from_log(log).game_uid == negotiated["game_uid"]


def test_the_two_sided_result_outranks_a_single_sides_peer_result(tmp_path: Path) -> None:
    """Precedence, not preference (caught by the M1 replay pin when this fix landed): a
    LOCAL log carries the two-sided `result` and both sides' `peer_result`, and a
    `peer_result` counts only its own side's steps — 4 where the match played 5."""
    log_path = tmp_path / "local.jsonl"
    match = run_local_minigame(Path("config"), police_seed=11, thief_seed=22, log_path=log_path)
    events = read_events(log_path)
    assert {e["event"] for e in events} >= {"result", "peer_result"}  # both present
    assert replay_from_log(log_path).steps == match.steps


def test_an_empty_log_is_tampered_not_vacuously_verified(tmp_path: Path) -> None:
    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    summary = replay_from_log(empty)
    assert summary.records_verified == 0
    assert verdict_for(summary) == VERDICT_TAMPERED


def test_a_log_truncated_before_the_audit_is_tampered(tmp_path: Path) -> None:
    """The aborted-game shape (kept fail-closed and disclosed): turns traveled, no
    record was ever revealed, so there is nothing to verify and nothing to trust."""
    lines = a_live_peer_log().read_text(encoding="utf-8").splitlines()
    kept = [
        line
        for line in lines
        if json.loads(line)["event"] not in ("audit", "audit_answer", "audit_received")
    ]
    truncated = tmp_path / "truncated.jsonl"
    truncated.write_text("\n".join(kept) + "\n", encoding="utf-8")
    summary = replay_from_log(truncated)
    assert summary.records_verified == 0
    assert verdict_for(summary) == VERDICT_TAMPERED

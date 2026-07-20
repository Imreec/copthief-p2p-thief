"""M6-6 summary builder: PeerSession + PeerGameResult -> the reference-shaped
per-sub-game summary the report builders consume (PRD_reporting §3/§6)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from copthief_core.domain.state_machine import GameState
from copthief_core.peer.sealing import seal_spec_record
from copthief_core.peer.session import PeerSession
from copthief_core.peer.settlement import PeerGameResult
from copthief_core.peer.summary_build import build_summary
from copthief_core.shared.config import load_all

CONSTITUTION, _SHIPPED, _LIMITS = load_all(Path("config"), counted=False)
PRIVATE = replace(_SHIPPED, police_class="random", thief_class="random")


def _played_thief() -> PeerSession:
    spec = seal_spec_record(
        spec={"os": "TestOS"},
        model="none",
        group_name=PRIVATE.group_name,
        sub_game_number=1,
        github_commit="ab" * 20,
        num_games_declared=2,
        scent_model_sha256="deadbeef",
    )
    thief = PeerSession(CONSTITUTION, PRIVATE, role="thief", seed=2, spec_record=spec)
    police = PeerSession(CONSTITUTION, PRIVATE, role="police", seed=1)
    thief.handle_negotiate(police.negotiate_payload())
    police.handle_negotiate(thief.negotiate_payload())
    police.handle_receive_turn(thief.take_turn(now=1.0))  # F2: the thief moves first
    thief.handle_receive_turn(police.take_turn(now=2.0))  # one inbound -> history
    thief.take_turn(now=3.0)
    return thief


def _result(session: PeerSession, *, outcome: str, audit_ok: bool = True) -> PeerGameResult:
    return PeerGameResult(
        role=session.role,
        outcome=outcome,
        steps=len(session.records),
        game_uid=session.game_uid or "",
        audit_ok=audit_ok,
        opponent_claim="capture",
        problems=(),
        opponent_records=3,
    )


def test_summary_matches_the_reference_shape_and_wire_vocabulary() -> None:
    session = _played_thief()
    session.outcome = "cop_capture"
    for state in (GameState.VERIFYING, GameState.GAME_OVER):
        if session.machine.state is not GameState.GAME_OVER:
            session.machine.advance(state)
    summary = build_summary(
        session,
        _result(session, outcome="cop_capture"),
        sub_game_number=1,
        started_at="2026-07-19T10:00:00+00:00",
        duration_seconds=12.34,
    )
    assert summary["result"] == "capture"  # wire vocabulary, never internal strings
    assert summary["winner"] == "police"
    assert summary["role"] == "thief"
    assert summary["sub_game_number"] == 1
    assert summary["steps"] == len(session.records)
    assert summary["tokens_total"] == 0
    assert summary["started_at"] == "2026-07-19T10:00:00+00:00"
    assert summary["duration_seconds"] == 12.34
    assert summary["group_name"] == PRIVATE.group_name


def test_summary_records_lead_with_the_spec_record_and_history_is_verbatim() -> None:
    session = _played_thief()
    summary = build_summary(
        session,
        _result(session, outcome="thief_survival"),
        sub_game_number=1,
        started_at="t",
        duration_seconds=1.0,
    )
    assert summary["records"][0]["payload"]["type"] == "system_spec"
    assert summary["records"][1]["payload"]["step"] == 1
    assert len(summary["records"]) == 1 + len(session.records)
    assert len(summary["history"]) == len(session.inbound) == 1
    assert summary["history"][0]["sender"] == "police"
    assert "commit" in summary["history"][0]
    assert "smell_grid" in summary["history"][0]


def test_summary_audit_block_reports_the_opponent_verification() -> None:
    session = _played_thief()
    ok = build_summary(
        session,
        _result(session, outcome="thief_survival", audit_ok=True),
        sub_game_number=1,
        started_at="t",
        duration_seconds=1.0,
    )
    assert ok["audit"] == {"passed": True, "verified_steps": 3, "failed_steps": []}
    failed = build_summary(
        session,
        replace(
            _result(session, outcome="thief_survival", audit_ok=False),
            problems=("tamper: step 2",),
        ),
        sub_game_number=1,
        started_at="t",
        duration_seconds=1.0,
    )
    assert failed["audit"]["passed"] is False
    assert failed["audit"]["failed_steps"] == ["tamper: step 2"]


def test_technical_outcomes_pass_through_with_no_winner() -> None:
    session = _played_thief()
    summary = build_summary(
        session,
        _result(session, outcome="timeout"),
        sub_game_number=2,
        started_at="t",
        duration_seconds=0.5,
    )
    assert summary["result"] == "timeout"
    assert summary["winner"] is None

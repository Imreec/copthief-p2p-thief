"""Audit flow (PLAN §4; kit §3): build, verify with OUR serializer, tamper detection."""

from copthief_core.peer.audit_flow import build_audit, derive_result, verify_audit
from copthief_core.peer.sealing import seal_turn
from copthief_core.wire.audit import AuditPayload


def _records(n: int) -> list:
    return [
        seal_turn(
            step=i,
            grid_size=7,
            position=(i % 7, 3),
            barriers=frozenset(),
            move="STAY",
            intent="truth",
            hint="I drift with the crowd.",
        )
        for i in range(1, n + 1)
    ]


def test_built_audit_verifies_cleanly() -> None:
    audit = AuditPayload.from_wire(build_audit("police", _records(5), {"result": "pending"}))
    assert verify_audit(audit) == []


def test_tampered_record_is_flagged_with_its_step() -> None:
    wire = build_audit("police", _records(5), {"result": "pending"})
    wire["records"][2]["payload"]["move"] = "MOVE:N"  # rewrite history after sealing
    problems = verify_audit(AuditPayload.from_wire(wire))
    assert any("step 3" in p for p in problems)


def test_wrong_nonce_is_flagged() -> None:
    wire = build_audit("police", _records(3), {"result": "pending"})
    wire["records"][0]["nonce"] = "0f" * 16
    problems = verify_audit(AuditPayload.from_wire(wire))
    assert any("step 1" in p for p in problems)


def test_step_gap_is_flagged() -> None:
    records = _records(4)
    del records[1]  # steps 1,3,4
    problems = verify_audit(AuditPayload.from_wire(build_audit("police", records, {})))
    assert any("continuity" in p for p in problems)


def test_audit_in_a_wrong_state_collapses_the_session() -> None:
    from pathlib import Path

    import pytest

    from copthief_core.domain.state_machine import GameState
    from copthief_core.peer.audit_flow import handle_submit_audit
    from copthief_core.peer.session import PeerSession, ProtocolViolationError
    from copthief_core.shared.config import load_all

    constitution, private, _ = load_all(Path("config"), counted=False)
    session = PeerSession(constitution, private, role="thief", seed=1)  # WAITING state
    with pytest.raises(ProtocolViolationError, match="audit arrived"):
        handle_submit_audit(session, build_audit("police", _records(1), {}))
    assert session.machine.state is GameState.TECHNICAL_LOSS


def test_malformed_audit_wire_collapses_the_last_mover() -> None:
    from pathlib import Path

    import pytest

    from copthief_core.domain.state_machine import GameState
    from copthief_core.peer.audit_flow import handle_submit_audit
    from copthief_core.peer.session import PeerSession, ProtocolViolationError
    from copthief_core.shared.config import load_all

    constitution, private, _ = load_all(Path("config"), counted=False)
    session = PeerSession(constitution, private, role="police", seed=1)
    session.take_turn(now=1.0)  # -> AWAITING_REVEAL, the last-mover audit-arrival state
    with pytest.raises(ProtocolViolationError, match="records"):
        handle_submit_audit(session, {"sender": "thief", "records": "oops", "result_claim": {}})
    assert session.machine.state is GameState.TECHNICAL_LOSS


def test_result_derives_from_record_count_never_from_claims() -> None:
    assert derive_result(steps_survived=35, survival_threshold=35, max_moves=35) == "thief_survival"
    assert derive_result(steps_survived=10, survival_threshold=35, max_moves=35) == "incomplete"

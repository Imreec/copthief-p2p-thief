"""Audit flow (PLAN §4; kit §3): build, verify with OUR serializer, tamper detection."""

from copthief_core.domain.crypto import commit as crypto_commit
from copthief_core.domain.crypto import make_nonce
from copthief_core.peer.audit_flow import build_audit, verify_audit
from copthief_core.peer.sealing import SealedTurn, seal_turn
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
    audit = AuditPayload.from_wire(build_audit("police", _records(5), "pending"))
    assert verify_audit(audit) == []


def test_tampered_record_is_flagged_with_its_step() -> None:
    wire = build_audit("police", _records(5), "pending")
    wire["records"][2]["payload"]["move"] = "MOVE:N"  # rewrite history after sealing
    problems = verify_audit(AuditPayload.from_wire(wire))
    assert any("step 3" in p for p in problems)


def test_wrong_nonce_is_flagged() -> None:
    wire = build_audit("police", _records(3), "pending")
    wire["records"][0]["nonce"] = "0f" * 16
    problems = verify_audit(AuditPayload.from_wire(wire))
    assert any("step 1" in p for p in problems)


def test_step_gap_is_flagged() -> None:
    records = _records(4)
    del records[1]  # steps 1,3,4
    problems = verify_audit(AuditPayload.from_wire(build_audit("police", records, "pending")))
    assert any("continuity" in p for p in problems)


def test_wire_result_speaks_the_reference_vocabulary() -> None:
    from copthief_core.peer.audit_flow import wire_result

    assert wire_result("thief_survival") == "survival"
    assert wire_result("cop_capture") == "capture"
    assert wire_result("timeout") == "timeout"


def test_reference_step0_spec_record_is_rehashed_not_continuity_checked() -> None:
    # The reference's audit includes a step-0 system_spec record before the game steps
    # (observed in the M2 smoke log: 36 verified records for 35 turns). Continuity
    # applies to the game steps (1..N); the spec record is still re-hashed.
    spec_payload = {"step": 0, "type": "system_spec", "spec": {"os": "x"}}
    nonce = make_nonce()
    spec_record = SealedTurn(
        payload=spec_payload, nonce=nonce, commit=crypto_commit(spec_payload, nonce)
    )
    wire = build_audit("thief", [spec_record, *_records(3)], "survival")
    assert verify_audit(AuditPayload.from_wire(wire)) == []


def test_tampered_step0_spec_record_is_still_caught() -> None:
    spec_payload = {"step": 0, "type": "system_spec", "spec": {"os": "x"}}
    nonce = make_nonce()
    spec_record = SealedTurn(
        payload=spec_payload, nonce=nonce, commit=crypto_commit(spec_payload, nonce)
    )
    wire = build_audit("thief", [spec_record, *_records(3)], "survival")
    wire["records"][0]["payload"]["spec"] = {"os": "rewritten"}
    problems = verify_audit(AuditPayload.from_wire(wire))
    assert any("step 0" in p for p in problems)

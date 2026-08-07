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


def test_trailing_repeated_final_step_is_the_reference_caught_convention() -> None:
    # Live finding (M5 friendly g2): a caught reference thief seals its mandatory
    # final message at its CURRENT step - revealed steps run [1..N, N]. That single
    # trailing repeat is legal; the records still re-hash individually.
    records = _records(4)
    final = seal_turn(
        step=4,
        grid_size=7,
        position=(4 % 7, 3),
        barriers=frozenset(),
        move="STAY",
        intent="truth",
        hint="You got me.",
    )
    audit = AuditPayload.from_wire(build_audit("thief", [*records, final], "capture"))
    assert verify_audit(audit) == []


def test_a_mid_series_repeated_step_still_breaks_continuity() -> None:
    records = _records(4)
    dup = records[1]  # a second step-2 record inserted mid-series
    wire = build_audit("thief", [*records[:2], dup, *records[2:]], "capture")
    problems = verify_audit(AuditPayload.from_wire(wire))
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


def _sealed_meta(payload: dict) -> dict:
    """One sealed NON-GAME record (a control message or a step-0 declaration).

    Built directly rather than through seal_turn: the point of the fixture is a record
    whose payload is not a game move, which seal_turn cannot produce.
    """
    nonce = make_nonce()
    return {"payload": payload, "nonce": nonce, "commit": crypto_commit(payload, nonce)}


def test_control_records_sharing_game_step_numbers_do_not_break_continuity() -> None:
    """Live finding (uoh-sqak friendly g01, 2026-08-06): a peer that seals its control
    messages into the same chain, numbered in the GAME step space, made every one of our
    audits fail — revealed steps read [1, 2, 1, 2, 3, ... 35]. Continuity is about the
    game; a record that declares itself `control` is not a game step.
    """
    wire = build_audit("thief", _records(35), "survival")
    for step, kind in ((1, "status"), (2, "status")):
        wire["records"].insert(
            step - 1,
            _sealed_meta(
                {
                    "direction": "sent",
                    "kind": kind,
                    "sender": "thief",
                    "status": "PLAYING",
                    "step": step,
                    "sub_game_number": 1,
                    "type": "control",
                }
            ),
        )
    assert verify_audit(AuditPayload.from_wire(wire)) == []


def test_step_zero_declaration_is_excluded_by_its_type_too() -> None:
    """The reference's step-0 `system_spec` was excluded by its step number; excluding it
    by TYPE must keep working even when a peer numbers it inside the game space."""
    wire = build_audit("police", _records(3), "pending")
    wire["records"].insert(
        0, _sealed_meta({"step": 1, "sub_game_number": 1, "type": "system_spec"})
    )
    assert verify_audit(AuditPayload.from_wire(wire)) == []


def test_a_tampered_control_record_is_still_caught() -> None:
    """Excluding a record from CONTINUITY must never exclude it from the tamper check."""
    wire = build_audit("thief", _records(3), "survival")
    wire["records"].insert(0, _sealed_meta({"kind": "status", "step": 1, "type": "control"}))
    wire["records"][0]["payload"]["status"] = "REWRITTEN"
    assert any("tamper" in p for p in verify_audit(AuditPayload.from_wire(wire)))


def test_an_unknown_record_type_still_counts_as_a_game_step() -> None:
    """Fail-visible, not fail-open: only KNOWN non-game types are excused, so a peer
    inventing a type cannot silently empty the continuity check."""
    wire = build_audit("police", _records(3), "pending")
    wire["records"].insert(0, _sealed_meta({"step": 1, "type": "something_new"}))
    assert any("continuity" in p for p in verify_audit(AuditPayload.from_wire(wire)))


def test_negatively_numbered_records_are_excluded_whatever_their_type() -> None:
    """uoh-sqak's durable fix (2026-08-06): they stamp every non-move sealed record with a
    descending negative step, so a `step >= 1` filter excuses them with no agreement about
    type names. Pinned because it is the path that protects us from types we have never
    heard of — the closed set above can only name types that existed when it was written.
    """
    wire = build_audit("thief", _records(3), "survival")
    for offset, kind in enumerate(("control", "equivocation", "a_type_we_never_heard_of")):
        wire["records"].insert(0, _sealed_meta({"step": -1 - offset, "type": kind}))
    assert verify_audit(AuditPayload.from_wire(wire)) == []

"""AuditPayload + ControlMessage validation (PLAN §6): the audit is the trust anchor.

Shapes pinned against the running reference at M2 (oracle sha 960499fd, spike notes §2
F5/F6): `result_claim` is a plain result string, and ControlMessage carries the
reference's control-channel field set keyed by `kind`.
"""

import pytest

from copthief_core.wire.audit import AuditPayload, ControlMessage
from copthief_core.wire.validation import WireValidationError

RECORD = {
    "payload": {"step": 1, "move": "MOVE:S", "intent": "truth", "hint": "by the docks"},
    "nonce": "112233445566778899aabbccddeeff00",
    "commit": "b" * 64,
}
VALID_AUDIT = {
    "sender": "police",
    "records": [RECORD],
    "result_claim": "survival",
}
CONTROL_KEYS = {"kind", "sender", "sub_game_number", "status", "step_budget", "payload"}


def test_valid_audit_parses_with_typed_records() -> None:
    audit = AuditPayload.from_wire(VALID_AUDIT)
    assert audit.sender == "police"
    assert len(audit.records) == 1
    assert audit.records[0].payload["move"] == "MOVE:S"
    assert audit.records[0].nonce == RECORD["nonce"]
    assert audit.result_claim == "survival"


@pytest.mark.parametrize("missing", ["sender", "records", "result_claim"])
def test_each_missing_audit_field_is_rejected_by_name(missing: str) -> None:
    raw = {k: v for k, v in VALID_AUDIT.items() if k != missing}
    with pytest.raises(WireValidationError, match=missing):
        AuditPayload.from_wire(raw)


def test_non_string_result_claim_is_rejected() -> None:
    # The reference sends "capture" | "survival" | "timeout" as a plain string.
    with pytest.raises(WireValidationError, match="result_claim"):
        AuditPayload.from_wire({**VALID_AUDIT, "result_claim": {"outcome": "survival"}})


def test_malformed_records_are_rejected_with_their_index() -> None:
    bad_nonce = {**VALID_AUDIT, "records": [RECORD, {**RECORD, "nonce": 5}]}
    with pytest.raises(WireValidationError, match=r"records\[1\]"):
        AuditPayload.from_wire(bad_nonce)
    bad_commit = {**VALID_AUDIT, "records": [{**RECORD, "commit": "short"}]}
    with pytest.raises(WireValidationError, match=r"records\[0\]"):
        AuditPayload.from_wire(bad_commit)
    not_a_dict_payload = {**VALID_AUDIT, "records": [{**RECORD, "payload": "sealed"}]}
    with pytest.raises(WireValidationError, match=r"records\[0\]"):
        AuditPayload.from_wire(not_a_dict_payload)


def test_audit_round_trip_keeps_payload_dicts_verbatim() -> None:
    audit = AuditPayload.from_wire(VALID_AUDIT)
    assert AuditPayload.from_wire(audit.to_wire()) == audit
    assert audit.to_wire()["records"][0]["payload"] == RECORD["payload"]


def test_audit_tolerates_unknown_fields() -> None:
    audit = AuditPayload.from_wire({**VALID_AUDIT, "chain_head": "f" * 64})
    assert audit.extras == {"chain_head": "f" * 64}
    assert audit.to_wire()["chain_head"] == "f" * 64


def test_empty_records_list_is_valid_shape() -> None:
    audit = AuditPayload.from_wire({**VALID_AUDIT, "records": []})
    assert audit.records == ()


def test_non_object_record_entry_is_rejected() -> None:
    with pytest.raises(WireValidationError, match=r"records\[0\]: must be an object"):
        AuditPayload.from_wire({**VALID_AUDIT, "records": ["sealed-blob"]})


def test_valid_control_message_parses_with_reference_defaults() -> None:
    msg = ControlMessage.from_wire({"kind": "status", "sender": "thief"})
    assert msg.kind == "status"
    assert msg.sub_game_number == 1
    assert msg.status == ""
    assert msg.step_budget == 0.0
    assert msg.payload is None


def test_control_kind_outside_the_contract_is_rejected() -> None:
    with pytest.raises(WireValidationError, match="kind"):
        ControlMessage.from_wire({"kind": "surrender", "sender": "thief"})
    with pytest.raises(WireValidationError, match="sender"):
        ControlMessage.from_wire({"kind": "quit"})


def test_control_enable_kind_is_part_of_the_contract() -> None:
    # The reference's bidirectional-channel opt-in handshake starts with kind="enable".
    msg = ControlMessage.from_wire({"kind": "enable", "sender": "police"})
    assert msg.kind == "enable"


def test_control_round_trip_carries_the_reference_field_set() -> None:
    raw = {
        "kind": "status",
        "sender": "thief",
        "sub_game_number": 2,
        "status": "THINKING",
        "step_budget": 12.5,
        "payload": {"note": "resync"},
    }
    msg = ControlMessage.from_wire(raw)
    assert ControlMessage.from_wire(msg.to_wire()) == msg
    assert set(msg.to_wire()) == CONTROL_KEYS


def test_control_tolerates_unknown_fields_inbound() -> None:
    msg = ControlMessage.from_wire({"kind": "quit", "sender": "thief", "ping": 1})
    assert msg.extras == {"ping": 1}
    assert set(msg.to_wire()) == CONTROL_KEYS

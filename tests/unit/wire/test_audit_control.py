"""AuditPayload + ControlMessage validation (PLAN §6): the audit is the trust anchor."""

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
    "result_claim": {"outcome": "thief_survival", "steps": 35},
}


def test_valid_audit_parses_with_typed_records() -> None:
    audit = AuditPayload.from_wire(VALID_AUDIT)
    assert audit.sender == "police"
    assert len(audit.records) == 1
    assert audit.records[0].payload["move"] == "MOVE:S"
    assert audit.records[0].nonce == RECORD["nonce"]


@pytest.mark.parametrize("missing", ["sender", "records", "result_claim"])
def test_each_missing_audit_field_is_rejected_by_name(missing: str) -> None:
    raw = {k: v for k, v in VALID_AUDIT.items() if k != missing}
    with pytest.raises(WireValidationError, match=missing):
        AuditPayload.from_wire(raw)


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


def test_valid_control_message_parses() -> None:
    msg = ControlMessage.from_wire({"sender": "thief", "action": "status"})
    assert msg.action == "status"
    assert msg.message is None


def test_control_action_outside_the_contract_is_rejected() -> None:
    with pytest.raises(WireValidationError, match="action"):
        ControlMessage.from_wire({"sender": "thief", "action": "surrender"})
    with pytest.raises(WireValidationError, match="sender"):
        ControlMessage.from_wire({"action": "quit"})


def test_non_object_record_entry_is_rejected() -> None:
    with pytest.raises(WireValidationError, match=r"records\[0\]: must be an object"):
        AuditPayload.from_wire({**VALID_AUDIT, "records": ["sealed-blob"]})


def test_non_string_control_message_is_rejected() -> None:
    with pytest.raises(WireValidationError, match="message"):
        ControlMessage.from_wire({"sender": "thief", "action": "quit", "message": 42})


def test_control_round_trip_with_message_and_extras() -> None:
    raw = {"sender": "thief", "action": "restart", "message": "resync please", "ping": 1}
    msg = ControlMessage.from_wire(raw)
    assert ControlMessage.from_wire(msg.to_wire()) == msg
    assert msg.to_wire()["ping"] == 1

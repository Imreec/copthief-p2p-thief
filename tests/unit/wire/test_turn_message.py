"""TurnMessage validation (PLAN §6; PRD FR-2): reject-missing, tolerate-unknown, round-trip.

Shapes pinned against the running reference at M2 (oracle sha 960499fd, spike notes §2 F5/F6):
ISO-8601 string timestamp, cell-shaped capture_claim, dict claim_response/win_claim, and the
asdict()-parity outbound key set (all ten keys, explicit nulls, extras never emitted).
"""

import pytest

from copthief_core.wire.turn import TurnMessage
from copthief_core.wire.validation import WireValidationError

VALID = {
    "step": 3,
    "sender": "police",
    "hint": "I keep to the main avenues.",
    "smell_grid": {"2,3": 0.9, "2,4": 0.6},
    "commit": "a" * 64,
    "timestamp": "2026-07-17T11:11:56.649763+00:00",
}
WIRE_KEYS = {
    "step",
    "sender",
    "hint",
    "smell_grid",
    "commit",
    "timestamp",
    "barrier_placed",
    "capture_claim",
    "claim_response",
    "win_claim",
}


def test_valid_message_parses_with_typed_fields() -> None:
    msg = TurnMessage.from_wire(VALID)
    assert msg.step == 3
    assert msg.sender == "police"
    assert msg.smell_grid == {"2,3": 0.9, "2,4": 0.6}
    assert msg.barrier_placed is None
    assert msg.capture_claim is None


@pytest.mark.parametrize("missing", ["step", "sender", "hint", "smell_grid", "commit", "timestamp"])
def test_each_missing_required_field_is_rejected_by_name(missing: str) -> None:
    raw = {k: v for k, v in VALID.items() if k != missing}
    with pytest.raises(WireValidationError, match=missing):
        TurnMessage.from_wire(raw)


def test_reference_style_explicit_nulls_are_accepted() -> None:
    # The reference's asdict() serialization always emits unset optionals as null.
    raw = {
        **VALID,
        "barrier_placed": None,
        "capture_claim": None,
        "claim_response": None,
        "win_claim": None,
    }
    msg = TurnMessage.from_wire(raw)
    assert msg.barrier_placed is None
    assert msg.capture_claim is None
    assert msg.claim_response is None
    assert msg.win_claim is None


def test_outbound_wire_carries_exactly_the_reference_key_set() -> None:
    # The reference's from_dict does cls(**data): an unknown outbound key would CRASH
    # its turn handler, so to_wire emits the full ten-key set and nothing else.
    wire = TurnMessage.from_wire(VALID).to_wire()
    assert set(wire) == WIRE_KEYS
    assert wire["barrier_placed"] is None
    assert wire["capture_claim"] is None
    assert wire["claim_response"] is None
    assert wire["win_claim"] is None


def test_unknown_fields_are_tolerated_inbound_but_never_emitted() -> None:
    raw = {**VALID, "future_extension": {"x": 1}, "mood": "smug"}
    msg = TurnMessage.from_wire(raw)
    assert msg.extras == {"future_extension": {"x": 1}, "mood": "smug"}
    assert set(msg.to_wire()) == WIRE_KEYS


def test_round_trip_with_reference_shaped_optionals_is_lossless() -> None:
    raw = {
        **VALID,
        "barrier_placed": [2, 3],
        "capture_claim": [4, 4],
        "claim_response": {"claim": [4, 4], "caught": False},
        "win_claim": {"type": "survival"},
    }
    msg = TurnMessage.from_wire(raw)
    assert msg.capture_claim == (4, 4)
    assert msg.claim_response == {"claim": [4, 4], "caught": False}
    assert msg.win_claim == {"type": "survival"}
    assert TurnMessage.from_wire(msg.to_wire()) == msg


def test_bad_step_and_timestamp_types_are_rejected() -> None:
    with pytest.raises(WireValidationError, match="step"):
        TurnMessage.from_wire({**VALID, "step": "three"})
    with pytest.raises(WireValidationError, match="step"):
        TurnMessage.from_wire({**VALID, "step": -1})
    with pytest.raises(WireValidationError, match="timestamp"):
        TurnMessage.from_wire({**VALID, "timestamp": 1752690000.5})


def test_malformed_smell_grid_is_rejected() -> None:
    with pytest.raises(WireValidationError, match="smell_grid"):
        TurnMessage.from_wire({**VALID, "smell_grid": {"2;3": 0.9}})
    with pytest.raises(WireValidationError, match="smell_grid"):
        TurnMessage.from_wire({**VALID, "smell_grid": {"2,3": "strong"}})
    with pytest.raises(WireValidationError, match="smell_grid"):
        TurnMessage.from_wire({**VALID, "smell_grid": [0.9]})


def test_malformed_commit_is_rejected() -> None:
    with pytest.raises(WireValidationError, match="commit"):
        TurnMessage.from_wire({**VALID, "commit": "zz" * 32})
    with pytest.raises(WireValidationError, match="commit"):
        TurnMessage.from_wire({**VALID, "commit": "abc123"})


def test_malformed_cells_and_claims_are_rejected() -> None:
    with pytest.raises(WireValidationError, match="barrier_placed"):
        TurnMessage.from_wire({**VALID, "barrier_placed": [1]})
    with pytest.raises(WireValidationError, match="capture_claim"):
        TurnMessage.from_wire({**VALID, "capture_claim": True})
    with pytest.raises(WireValidationError, match="claim_response"):
        TurnMessage.from_wire({**VALID, "claim_response": False})
    with pytest.raises(WireValidationError, match="claim_response"):
        TurnMessage.from_wire({**VALID, "claim_response": {"claim": [4, 4]}})
    with pytest.raises(WireValidationError, match="win_claim"):
        TurnMessage.from_wire({**VALID, "win_claim": "survival"})
    with pytest.raises(WireValidationError, match="win_claim"):
        TurnMessage.from_wire({**VALID, "win_claim": {}})


def test_all_problems_reported_at_once() -> None:
    raw = {"sender": "", "hint": 7}
    with pytest.raises(WireValidationError) as excinfo:
        TurnMessage.from_wire(raw)
    text = str(excinfo.value)
    for name in ("step", "sender", "hint", "smell_grid", "commit", "timestamp"):
        assert name in text

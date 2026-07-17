"""TurnMessage validation (PLAN §6; PRD FR-2): reject-missing, tolerate-unknown, round-trip."""

import pytest

from copthief_core.wire.turn import TurnMessage
from copthief_core.wire.validation import WireValidationError

VALID = {
    "step": 3,
    "sender": "police",
    "hint": "I keep to the main avenues.",
    "smell_grid": {"2,3": 0.9, "2,4": 0.6},
    "commit": "a" * 64,
    "timestamp": 1752690000.5,
}


def test_valid_message_parses_with_typed_fields() -> None:
    msg = TurnMessage.from_wire(VALID)
    assert msg.step == 3
    assert msg.sender == "police"
    assert msg.smell_grid == {"2,3": 0.9, "2,4": 0.6}
    assert msg.barrier_placed is None
    assert msg.capture_claim is False


@pytest.mark.parametrize("missing", ["step", "sender", "hint", "smell_grid", "commit", "timestamp"])
def test_each_missing_required_field_is_rejected_by_name(missing: str) -> None:
    raw = {k: v for k, v in VALID.items() if k != missing}
    with pytest.raises(WireValidationError, match=missing):
        TurnMessage.from_wire(raw)


def test_unknown_fields_are_tolerated_and_preserved() -> None:
    raw = {**VALID, "future_extension": {"x": 1}, "mood": "smug"}
    msg = TurnMessage.from_wire(raw)
    assert msg.extras == {"future_extension": {"x": 1}, "mood": "smug"}
    wire = msg.to_wire()
    assert wire["future_extension"] == {"x": 1}
    assert wire["mood"] == "smug"


def test_round_trip_is_lossless() -> None:
    raw = {**VALID, "barrier_placed": [2, 3], "capture_claim": True, "claim_response": False}
    msg = TurnMessage.from_wire(raw)
    assert TurnMessage.from_wire(msg.to_wire()) == msg


def test_win_claim_round_trips_when_present() -> None:
    msg = TurnMessage.from_wire({**VALID, "win_claim": "survival"})
    assert msg.win_claim == "survival"
    assert msg.to_wire()["win_claim"] == "survival"
    assert TurnMessage.from_wire(msg.to_wire()) == msg


def test_bad_step_and_timestamp_types_are_rejected() -> None:
    with pytest.raises(WireValidationError, match="step"):
        TurnMessage.from_wire({**VALID, "step": "three"})
    with pytest.raises(WireValidationError, match="step"):
        TurnMessage.from_wire({**VALID, "step": -1})
    with pytest.raises(WireValidationError, match="timestamp"):
        TurnMessage.from_wire({**VALID, "timestamp": "noon"})


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


def test_malformed_barrier_and_claims_are_rejected() -> None:
    with pytest.raises(WireValidationError, match="barrier_placed"):
        TurnMessage.from_wire({**VALID, "barrier_placed": [1]})
    with pytest.raises(WireValidationError, match="capture_claim"):
        TurnMessage.from_wire({**VALID, "capture_claim": "yes"})


def test_all_problems_reported_at_once() -> None:
    raw = {"sender": "", "hint": 7}
    with pytest.raises(WireValidationError) as excinfo:
        TurnMessage.from_wire(raw)
    text = str(excinfo.value)
    for name in ("step", "sender", "hint", "smell_grid", "commit", "timestamp"):
        assert name in text

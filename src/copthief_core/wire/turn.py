"""TurnMessage — the per-step wire message (interface-mirror of the reference, PLAN §6).

Carries the public face of a turn: the free-language hint, the transmitted smell grid,
and the sealed commit — never the move itself (hidden-position model; the move reveals
at audit). Unknown fields ride along in `extras` untouched: tolerate-unknown is the
forward-compatibility half of the FR-2 validation rule, reject-missing is the other.
The exact optional-field types are M2-verified against the live reference.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from copthief_core.wire.validation import (
    WireValidationError,
    check_hex64,
    check_int,
    check_number,
    check_optional_bool,
    check_optional_cell,
    check_smell_grid,
    check_str,
)

_KNOWN_KEYS = frozenset(
    {
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
)


@dataclass(frozen=True)
class TurnMessage:
    """One validated inbound/outbound turn (PLAN §6 field set)."""

    step: int
    sender: str
    hint: str
    smell_grid: dict[str, float]
    commit: str
    timestamp: float
    barrier_placed: tuple[int, int] | None = None
    capture_claim: bool = False
    claim_response: bool | None = None
    win_claim: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_wire(cls, raw: dict[str, Any]) -> TurnMessage:
        """Validate a raw dict BEFORE any state changes (Input: inbound payload;
        Output: typed message; Raises: WireValidationError naming every problem)."""
        problems = [
            p
            for p in (
                check_int(raw, "step", minimum=0),
                check_str(raw, "sender", non_empty=True),
                check_str(raw, "hint"),
                check_smell_grid(raw, "smell_grid"),
                check_hex64(raw, "commit"),
                check_number(raw, "timestamp"),
                check_optional_cell(raw, "barrier_placed"),
                check_optional_bool(raw, "capture_claim"),
                check_optional_bool(raw, "claim_response"),
                check_str(raw, "win_claim") if "win_claim" in raw else None,
            )
            if p is not None
        ]
        if problems:
            raise WireValidationError("TurnMessage", problems)
        barrier = raw.get("barrier_placed")
        return cls(
            step=raw["step"],
            sender=raw["sender"],
            hint=raw["hint"],
            smell_grid=dict(raw["smell_grid"]),
            commit=raw["commit"],
            timestamp=raw["timestamp"],
            barrier_placed=(barrier[0], barrier[1]) if barrier is not None else None,
            capture_claim=raw.get("capture_claim", False),
            claim_response=raw.get("claim_response"),
            win_claim=raw.get("win_claim"),
            extras={k: v for k, v in raw.items() if k not in _KNOWN_KEYS},
        )

    def to_wire(self) -> dict[str, Any]:
        """The outbound dict: required fields, set optionals, and extras merged back."""
        wire: dict[str, Any] = {
            "step": self.step,
            "sender": self.sender,
            "hint": self.hint,
            "smell_grid": dict(self.smell_grid),
            "commit": self.commit,
            "timestamp": self.timestamp,
        }
        if self.barrier_placed is not None:
            wire["barrier_placed"] = list(self.barrier_placed)
        if self.capture_claim:
            wire["capture_claim"] = True
        if self.claim_response is not None:
            wire["claim_response"] = self.claim_response
        if self.win_claim is not None:
            wire["win_claim"] = self.win_claim
        wire.update({k: v for k, v in self.extras.items() if k not in wire})
        return wire

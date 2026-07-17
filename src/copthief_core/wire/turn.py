"""TurnMessage — the per-step wire message (interface-mirror of the reference, PLAN §6).

Carries the public face of a turn: the free-language hint, the transmitted smell grid,
and the sealed commit — never the move itself (hidden-position model; the move reveals
at audit). Shapes pinned against the running reference (oracle sha 960499fd, spike notes
§2 F5/F6): ISO-8601 string timestamp; `capture_claim` is the claimed CELL; `claim_response`
and `win_claim` are dicts. Unknown inbound fields ride along in `extras` untouched
(tolerate-unknown, FR-2) but are NEVER emitted — the reference's `from_dict(**data)`
crashes on unknown keys, so `to_wire` mirrors its asdict() parity instead: always exactly
the ten known keys, unset optionals as explicit nulls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from copthief_core.wire.validation import (
    WireValidationError,
    check_hex64,
    check_int,
    check_optional_cell,
    check_optional_claim_response,
    check_optional_win_claim,
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
    """One validated inbound/outbound turn (PLAN §6 field set, reference-shaped)."""

    step: int
    sender: str
    hint: str
    smell_grid: dict[str, float]
    commit: str
    timestamp: str
    barrier_placed: tuple[int, int] | None = None
    capture_claim: tuple[int, int] | None = None
    claim_response: dict[str, Any] | None = None
    win_claim: dict[str, Any] | None = None
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
                check_str(raw, "timestamp", non_empty=True),
                check_optional_cell(raw, "barrier_placed"),
                check_optional_cell(raw, "capture_claim"),
                check_optional_claim_response(raw, "claim_response"),
                check_optional_win_claim(raw, "win_claim"),
            )
            if p is not None
        ]
        if problems:
            raise WireValidationError("TurnMessage", problems)
        barrier, claim = raw.get("barrier_placed"), raw.get("capture_claim")
        return cls(
            step=raw["step"],
            sender=raw["sender"],
            hint=raw["hint"],
            smell_grid=dict(raw["smell_grid"]),
            commit=raw["commit"],
            timestamp=raw["timestamp"],
            barrier_placed=(barrier[0], barrier[1]) if barrier is not None else None,
            capture_claim=(claim[0], claim[1]) if claim is not None else None,
            claim_response=raw.get("claim_response"),
            win_claim=raw.get("win_claim"),
            extras={k: v for k, v in raw.items() if k not in _KNOWN_KEYS},
        )

    def to_wire(self) -> dict[str, Any]:
        """The outbound dict: exactly the reference's ten-key set, nulls explicit.

        Cells go out as JSON arrays; `extras` are inbound-only bookkeeping and never
        cross the wire (the reference rejects unknown TurnMessage keys — F6).
        """
        return {
            "step": self.step,
            "sender": self.sender,
            "hint": self.hint,
            "smell_grid": dict(self.smell_grid),
            "commit": self.commit,
            "timestamp": self.timestamp,
            "barrier_placed": list(self.barrier_placed) if self.barrier_placed else None,
            "capture_claim": list(self.capture_claim) if self.capture_claim else None,
            "claim_response": self.claim_response,
            "win_claim": self.win_claim,
        }

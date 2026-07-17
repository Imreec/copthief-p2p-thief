"""AuditPayload + ControlMessage (interface-mirror of the reference, PLAN §6).

The audit payload is the trust anchor of the whole protocol: the opponent re-hashes every
revealed record in it (kit §3), so record `payload` dicts are carried VERBATIM — never
re-shaped — from wire to verifier. Shapes pinned against the running reference (oracle sha
960499fd, spike notes §2): `result_claim` is a plain result string; ControlMessage is the
opt-in control channel keyed by `kind` (enable/status/restart/quit) and is never sealed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from copthief_core.wire.validation import WireValidationError, check_hex64, check_str

_NONCE_FORM = re.compile(r"^[0-9a-f]+$")
_CONTROL_KINDS = frozenset({"enable", "status", "restart", "quit"})
_AUDIT_KEYS = frozenset({"sender", "records", "result_claim"})
_CONTROL_KEYS = frozenset({"kind", "sender", "sub_game_number", "status", "step_budget", "payload"})


@dataclass(frozen=True)
class SealedRecord:
    """One revealed record: the verbatim payload, its nonce, and the sealed commit."""

    payload: dict[str, Any]
    nonce: str
    commit: str


def _check_record(index: int, raw: object) -> str | None:
    """Shape-check one wire record; the index makes a cross-team failure diagnosable."""
    if not isinstance(raw, dict):
        return f"records[{index}]: must be an object, got {type(raw).__name__}"
    if not isinstance(raw.get("payload"), dict):
        return f"records[{index}]: payload must be an object"
    nonce = raw.get("nonce")
    if not isinstance(nonce, str) or not _NONCE_FORM.match(nonce):
        return f"records[{index}]: nonce must be a hex string"
    if check_hex64(raw, "commit") is not None:
        return f"records[{index}]: commit must be 64-char lowercase hex"
    return None


@dataclass(frozen=True)
class AuditPayload:
    """The end-of-game audit submission: all sealed records + the claimed result string."""

    sender: str
    records: tuple[SealedRecord, ...]
    result_claim: str
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_wire(cls, raw: dict[str, Any]) -> AuditPayload:
        """Validate before verification begins; every problem reported at once."""
        problems = [
            p
            for p in (
                check_str(raw, "sender", non_empty=True),
                check_str(raw, "result_claim", non_empty=True),
            )
            if p is not None
        ]
        records = raw.get("records")
        if not isinstance(records, list):
            problems.append(f"records: required list, got {type(records).__name__}")
            records = []
        problems.extend(
            p for p in (_check_record(i, r) for i, r in enumerate(records)) if p is not None
        )
        if problems:
            raise WireValidationError("AuditPayload", problems)
        return cls(
            sender=raw["sender"],
            records=tuple(
                SealedRecord(payload=r["payload"], nonce=r["nonce"], commit=r["commit"])
                for r in records
            ),
            result_claim=raw["result_claim"],
            extras={k: v for k, v in raw.items() if k not in _AUDIT_KEYS},
        )

    def to_wire(self) -> dict[str, Any]:
        """The outbound dict; record payloads pass through verbatim."""
        wire: dict[str, Any] = {
            "sender": self.sender,
            "records": [
                {"payload": r.payload, "nonce": r.nonce, "commit": r.commit} for r in self.records
            ],
            "result_claim": self.result_claim,
        }
        wire.update({k: v for k, v in self.extras.items() if k not in wire})
        return wire


@dataclass(frozen=True)
class ControlMessage:
    """Opt-in control channel (reference field set) — never sealed, never scored."""

    kind: str
    sender: str
    sub_game_number: int = 1
    status: str = ""
    step_budget: float = 0.0
    payload: dict[str, Any] | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_wire(cls, raw: dict[str, Any]) -> ControlMessage:
        """Validate sender + the closed kind set; unknown fields tolerated inbound."""
        problems = [p for p in (check_str(raw, "sender", non_empty=True),) if p is not None]
        if raw.get("kind") not in _CONTROL_KINDS:
            problems.append(
                f"kind: must be one of {sorted(_CONTROL_KINDS)}, got {raw.get('kind')!r}"
            )
        if problems:
            raise WireValidationError("ControlMessage", problems)
        return cls(
            kind=raw["kind"],
            sender=raw["sender"],
            sub_game_number=raw.get("sub_game_number", 1),
            status=raw.get("status", ""),
            step_budget=raw.get("step_budget", 0.0),
            payload=raw.get("payload"),
            extras={k: v for k, v in raw.items() if k not in _CONTROL_KEYS},
        )

    def to_wire(self) -> dict[str, Any]:
        """The outbound dict: the reference's six-key set (asdict parity), extras never."""
        return {
            "kind": self.kind,
            "sender": self.sender,
            "sub_game_number": self.sub_game_number,
            "status": self.status,
            "step_budget": self.step_budget,
            "payload": self.payload,
        }

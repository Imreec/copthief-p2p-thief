"""AuditPayload + ControlMessage (interface-mirror of the reference, PLAN §6).

The audit payload is the trust anchor of the whole protocol: the opponent re-hashes every
revealed record in it (kit §3), so record `payload` dicts are carried VERBATIM — never
re-shaped — from wire to verifier. ControlMessage is the opt-in status/restart/quit side
channel; it is never sealed. Both shapes are M2-verified against the live reference.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from copthief_core.wire.validation import WireValidationError, check_hex64, check_str

_NONCE_FORM = re.compile(r"^[0-9a-f]+$")
_CONTROL_ACTIONS = frozenset({"status", "restart", "quit"})
_AUDIT_KEYS = frozenset({"sender", "records", "result_claim"})
_CONTROL_KEYS = frozenset({"sender", "action", "message"})


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
    """The end-of-game audit submission: all sealed records + the derived result claim."""

    sender: str
    records: tuple[SealedRecord, ...]
    result_claim: dict[str, Any]
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_wire(cls, raw: dict[str, Any]) -> AuditPayload:
        """Validate before verification begins; every problem reported at once."""
        problems = [p for p in (check_str(raw, "sender", non_empty=True),) if p is not None]
        records = raw.get("records")
        if not isinstance(records, list):
            problems.append(f"records: required list, got {type(records).__name__}")
            records = []
        problems.extend(
            p for p in (_check_record(i, r) for i, r in enumerate(records)) if p is not None
        )
        if not isinstance(raw.get("result_claim"), dict):
            problems.append("result_claim: required object")
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
    """Opt-in status/restart/quit side channel — never sealed, never scored."""

    sender: str
    action: str
    message: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_wire(cls, raw: dict[str, Any]) -> ControlMessage:
        """Validate sender + the closed action set; unknown fields tolerated."""
        problems = [p for p in (check_str(raw, "sender", non_empty=True),) if p is not None]
        if raw.get("action") not in _CONTROL_ACTIONS:
            problems.append(
                f"action: must be one of {sorted(_CONTROL_ACTIONS)}, got {raw.get('action')!r}"
            )
        if "message" in raw and not isinstance(raw["message"], str):
            problems.append(f"message: must be a str when present, got {raw['message']!r}")
        if problems:
            raise WireValidationError("ControlMessage", problems)
        return cls(
            sender=raw["sender"],
            action=raw["action"],
            message=raw.get("message"),
            extras={k: v for k, v in raw.items() if k not in _CONTROL_KEYS},
        )

    def to_wire(self) -> dict[str, Any]:
        """The outbound dict; `message` emitted only when set."""
        wire: dict[str, Any] = {"sender": self.sender, "action": self.action}
        if self.message is not None:
            wire["message"] = self.message
        wire.update({k: v for k, v in self.extras.items() if k not in wire})
        return wire
